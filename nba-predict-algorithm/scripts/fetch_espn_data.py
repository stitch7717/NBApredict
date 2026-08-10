"""
从 ESPN API 抓取真实 NBA 比赛数据
支持 2022-23 到 2025-26 四个赛季
"""
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, Team

# 赛季配置: (espn_season_year, nba_season_label, start_date, end_date)
SEASONS = [
    (2023, "2022-23", datetime(2022, 10, 18), datetime(2023, 6, 20)),
    (2024, "2023-24", datetime(2023, 10, 24), datetime(2024, 6, 18)),
    (2025, "2024-25", datetime(2024, 10, 22), datetime(2025, 6, 15)),
    (2026, "2025-26", datetime(2025, 10, 22), datetime(2026, 6, 20)),
]

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"


# ESPN 使用的缩写与数据库不同的映射
ESPN_ABBR_FIX = {
    "GS": "GSW",   # Golden State Warriors
    "NO": "NOP",   # New Orleans Pelicans
    "UTAH": "UTA", # Utah Jazz
    "WSH": "WAS",  # Washington Wizards
    "NY": "NYK",   # New York Knicks
    "SA": "SAS",   # San Antonio Spurs
}


def get_team_abbr_map():
    """获取 abbreviation -> team_id 映射（含 ESPN 缩写修正）"""
    with SessionLocal() as db:
        teams = db.query(Team).all()
        result = {t.abbreviation: t.team_id for t in teams}
        # 添加 ESPN 缩写映射
        for espn_abbr, db_abbr in ESPN_ABBR_FIX.items():
            if db_abbr in result:
                result[espn_abbr] = result[db_abbr]
        return result


def fetch_week(d1: datetime, d2: datetime) -> list:
    """获取一周的比赛数据"""
    date_str = f"{d1.strftime('%Y%m%d')}-{d2.strftime('%Y%m%d')}"
    url = f"{ESPN_BASE}?dates={date_str}&limit=100"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get("events", [])
    except Exception as e:
        logger.warning(f"获取 {date_str} 失败: {e}")
        return []


def parse_game(event: dict, abbr_map: dict) -> dict:
    """解析单场比赛数据"""
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
            # 尝试用 displayName 匹配
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

    if not home or not away:
        return None
    if not home["team_id"] or not away["team_id"]:
        return None

    season_type = event.get("season", {}).get("type", 2)
    game_date_str = event.get("date", "")[:10]

    return {
        "espn_id": event.get("id"),
        "name": event.get("name"),
        "game_date": game_date_str,
        "home_team_id": home["team_id"],
        "away_team_id": away["team_id"],
        "home_score": home["score"],
        "away_score": away["score"],
        "home_abbr": home["abbr"],
        "away_abbr": away["abbr"],
        "is_playoff": 1 if season_type == 3 else 0,
        "season_type": season_type,
    }


def fetch_season(season_year: int, season_label: str, start: datetime, end: datetime, abbr_map: dict):
    """抓取单赛季所有比赛"""
    logger.info(f"抓取 {season_label} 赛季 ({start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')})")

    with SessionLocal() as db:
        existing = db.query(GameRecord).filter(GameRecord.season == season_label).count()
        if existing > 1200:
            logger.info(f"  已有 {existing} 条记录，跳过")
            return existing

    total_fetched = 0
    total_saved = 0
    current = start

    with SessionLocal() as db:
        while current < end:
            week_end = min(current + timedelta(days=6), end)
            events = fetch_week(current, week_end)
            total_fetched += len(events)

            for event in events:
                game = parse_game(event, abbr_map)
                if not game:
                    continue

                # 检查是否已存在
                exists = db.query(GameRecord).filter(
                    GameRecord.nba_game_id == f"espn_{game['espn_id']}"
                ).first()
                if exists:
                    continue

                gr = GameRecord(
                    nba_game_id=f"espn_{game['espn_id']}",
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
                total_saved += 1

            # 每周提交一次
            db.commit()
            current = week_end + timedelta(days=1)

    logger.info(f"  {season_label}: 抓取 {total_fetched} 场, 新增 {total_saved} 条")
    return total_saved


def run():
    logger.info("=" * 50)
    logger.info("ESPN 真实数据抓取开始")
    logger.info("=" * 50)

    abbr_map = get_team_abbr_map()
    logger.info(f"球队映射: {len(abbr_map)} 支球队")

    total = 0
    for year, label, start, end in SEASONS:
        count = fetch_season(year, label, start, end, abbr_map)
        total += count

    logger.info("=" * 50)
    logger.info(f"抓取完成, 共新增 {total} 条记录")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
