"""
补抓缺失球队的比赛数据
支持 ESPN + 新浪体育双源，自动重试 + 指数退避
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, Team

ESPN_ABBR_FIX = {
    "GS": "GSW", "NO": "NOP", "UTAH": "UTA",
    "WSH": "WAS", "NY": "NYK", "SA": "SAS",
}

TARGET_TEAM_IDS = [11, 15, 18, 24, 29, 30]

SEASONS = [
    ("2022-23", datetime(2022, 10, 18), datetime(2023, 6, 20)),
    ("2023-24", datetime(2023, 10, 24), datetime(2024, 6, 18)),
    ("2024-25", datetime(2024, 10, 22), datetime(2025, 6, 15)),
    ("2025-26", datetime(2025, 10, 22), datetime(2026, 6, 20)),
]

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ctx = ssl.create_default_context()

# 新浪体育 NBA 赛程 API
SINA_BASE = "https://nba.sports.sina.com.cn/nba_data/nba_match.php"


def fetch_json(url, retries=3, base_delay=2.0):
    """带指数退避的请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            if attempt < retries - 1:
                logger.debug(f"重试 {attempt+1}/{retries}，等待 {delay:.0f}s: {e}")
                time.sleep(delay)
            else:
                logger.warning(f"请求失败 ({retries}次): {url[:80]}... {e}")
    return {}


def get_team_abbr_map():
    with SessionLocal() as db:
        teams = db.query(Team).all()
        result = {t.abbreviation: t.team_id for t in teams}
        for espn_abbr, db_abbr in ESPN_ABBR_FIX.items():
            if db_abbr in result:
                result[espn_abbr] = result[db_abbr]
        return result


# ─── ESPN 数据源 ───

def fetch_espn_week(d1: datetime, d2: datetime) -> list:
    """获取一周比赛（减少请求数）"""
    date_str = f"{d1.strftime('%Y%m%d')}-{d2.strftime('%Y%m%d')}"
    url = f"{ESPN_BASE}?dates={date_str}&limit=100"
    data = fetch_json(url)
    return data.get("events", [])


def parse_espn_game(event: dict, abbr_map: dict) -> dict:
    comp = event.get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None

    home = away = None
    for c in competitors:
        team_info = c.get("team", {})
        abbr = team_info.get("abbreviation", "")
        score = int(c.get("score", "0"))
        team_id = abbr_map.get(abbr)
        if not team_id:
            display = team_info.get("displayName", "")
            for p_abbr, p_id in abbr_map.items():
                if p_abbr in display:
                    team_id = p_id
                    break
        entry = {"team_id": team_id, "abbr": abbr, "score": score}
        if c.get("homeAway") == "home":
            home = entry
        else:
            away = entry

    if not home or not away or not home["team_id"] or not away["team_id"]:
        return None
    if home["team_id"] not in TARGET_TEAM_IDS and away["team_id"] not in TARGET_TEAM_IDS:
        return None

    season_type = event.get("season", {}).get("type", 2)
    return {
        "espn_id": event.get("id"),
        "game_date": event.get("date", "")[:10],
        "home_team_id": home["team_id"],
        "away_team_id": away["team_id"],
        "home_score": home["score"],
        "away_score": away["score"],
        "is_playoff": 1 if season_type == 3 else 0,
    }


# ─── 新浪数据源（备用） ───

SINA_TEAM_MAP = {
    "纽约尼克斯": 11, "华盛顿奇才": 15, "金州勇士": 18,
    "新奥尔良鹈鹕": 24, "圣安东尼奥马刺": 29, "犹他爵士": 30,
    # 其他队也映射，方便匹配
    "亚特兰大老鹰": 1, "波士顿凯尔特人": 2, "布鲁克林篮网": 3,
    "夏洛特黄蜂": 4, "芝加哥公牛": 5, "克利夫兰骑士": 6,
    "底特律活塞": 7, "印第安纳步行者": 8, "迈阿密热火": 9,
    "密尔沃基雄鹿": 10, "奥兰多魔术": 12, "费城76人": 13,
    "多伦多猛龙": 14, "达拉斯独行侠": 16, "丹佛掘金": 17,
    "休斯顿火箭": 19, "洛杉矶快船": 20, "洛杉矶湖人": 21,
    "孟菲斯灰熊": 22, "明尼苏达森林狼": 23, "俄克拉荷马雷霆": 25,
    "菲尼克斯太阳": 26, "波特兰开拓者": 27, "萨克拉门托国王": 28,
}


def fetch_sina_month(year: int, month: int, abbr_map: dict) -> list:
    """从新浪体育获取某月比赛数据"""
    url = f"{SINA_BASE}?type=month&year={year}&month={month:02d}"
    data = fetch_json(url, retries=2, base_delay=3.0)
    games = []
    # 新浪返回格式可能变化，做防御性解析
    match_list = data.get("result", {}).get("data", [])
    if not match_list:
        match_list = data.get("data", [])
    if not match_list:
        return games

    for m in match_list:
        try:
            home_name = m.get("home_name", "") or m.get("home", "")
            away_name = m.get("away_name", "") or m.get("away", "")
            home_tid = SINA_TEAM_MAP.get(home_name)
            away_tid = SINA_TEAM_MAP.get(away_name)
            if not home_tid or not away_tid:
                continue
            if home_tid not in TARGET_TEAM_IDS and away_tid not in TARGET_TEAM_IDS:
                continue

            game_date = m.get("match_time", "")[:10] or m.get("date", "")[:10]
            hs = int(m.get("home_score", 0) or m.get("home_point", 0) or 0)
            as_ = int(m.get("away_score", 0) or m.get("away_point", 0) or 0)
            if hs == 0 and as_ == 0:
                continue

            games.append({
                "espn_id": f"sina_{year}{month:02d}_{m.get('match_id', '')}",
                "game_date": game_date,
                "home_team_id": home_tid,
                "away_team_id": away_tid,
                "home_score": hs,
                "away_score": as_,
                "is_playoff": 0,
            })
        except Exception:
            continue

    return games


# ─── 主逻辑 ───

def save_games(games: list, existing_ids: set, season_label: str, db) -> int:
    """批量写入比赛记录"""
    saved = 0
    for game in games:
        nba_game_id = f"espn_{game['espn_id']}"
        if nba_game_id in existing_ids:
            continue
        gr = GameRecord(
            nba_game_id=nba_game_id,
            season=season_label,
            game_date=game["game_date"],
            game_type="Playoffs" if game["is_playoff"] else "Regular Season",
            home_team_id=game["home_team_id"],
            away_team_id=game["away_team_id"],
            home_score=game["home_score"],
            away_score=game["away_score"],
            home_win=1 if game["home_score"] > game["away_score"] else 0,
            score_diff=game["home_score"] - game["away_score"],
            total_score=game["home_score"] + game["away_score"],
            is_playoff=game["is_playoff"],
            status="FINISHED",
        )
        db.add(gr)
        existing_ids.add(nba_game_id)
        saved += 1
    return saved


def run():
    abbr_map = get_team_abbr_map()
    logger.info(f"球队映射: {len(abbr_map)} 支")

    with SessionLocal() as db:
        existing_ids = set(g[0] for g in db.query(GameRecord.nba_game_id).all())

    total_saved = 0

    for season_label, start, end in SEASONS:
        logger.info(f"=== 补抓 {season_label} ===")
        season_saved = 0

        # ── ESPN 按周抓取 ──
        current = start
        with SessionLocal() as db:
            while current <= end:
                week_end = min(current + timedelta(days=6), end)
                events = fetch_espn_week(current, week_end)

                games = []
                for event in events:
                    g = parse_espn_game(event, abbr_map)
                    if g:
                        games.append(g)

                saved = save_games(games, existing_ids, season_label, db)
                season_saved += saved

                if saved > 0:
                    logger.info(f"  ESPN {current.strftime('%m-%d')} ~ {week_end.strftime('%m-%d')}: +{saved}")

                # 每 2 周提交一次
                if (current - start).days % 14 == 0:
                    db.commit()

                current = week_end + timedelta(days=1)
                time.sleep(0.3)  # 限速

            db.commit()

        # ── 新浪备用源（按月补漏） ──
        logger.info(f"  ESPN 完成 {season_saved} 场，尝试新浪补漏...")
        current = start
        with SessionLocal() as db:
            while current <= end:
                sina_games = fetch_sina_month(current.year, current.month, abbr_map)
                saved = save_games(sina_games, existing_ids, season_label, db)
                if saved > 0:
                    logger.info(f"  新浪 {current.strftime('%Y-%m')}: +{saved}")
                season_saved += saved
                current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
                time.sleep(1.0)

            db.commit()

        logger.info(f"  {season_label} 合计: +{season_saved}")
        total_saved += season_saved

    logger.info(f"\n补抓完成, 共新增 {total_saved} 场")

    # 最终统计
    with SessionLocal() as db:
        teams = {t.team_id: t.abbreviation for t in db.query(Team).all()}
        from collections import Counter
        counts = Counter()
        for g in db.query(GameRecord).all():
            counts[g.home_team_id] += 1
            counts[g.away_team_id] += 1
        logger.info("=== 缺失球队比赛数 ===")
        for tid in TARGET_TEAM_IDS:
            logger.info(f"  {teams.get(tid, '?')}: {counts[tid]} 场")


if __name__ == "__main__":
    run()
