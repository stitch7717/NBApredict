"""
从 ESPN 公开 API 采集 10 个赛季的全部比赛记录（比分/胜负），并与库内已有数据对账:
- 按月分段调用 scoreboard（单次上限 ~1000 场），事件缓存到 data/espn_events_cache.json
- 全部赛季事件先收集完，再做一次全局对账:
    * 匹配库内已有比赛（按 日期+主队+客队）：分数/赛季标签错误则修正
    * 库内没有的比赛: 插入（nba_game_id = 'espn_<id>'）
    * ESPN 没有的库内行（重复/多余数据）: 删除
- 对账后清掉 series_star 中悬空的 key_game_id 引用

用法:
    python scripts/fetch_espn_games.py [--refresh-cache] [--dry-run]
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, SeriesStar, Team

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
PROXY = "http://127.0.0.1:7897"
REQUEST_DELAY = 0.4
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "espn_events_cache.json"

# 每赛季的时间范围（含 2019-20 泡泡赛季和 2020-21 延迟赛季）
SEASON_RANGES = {
    "2016-17": ("2016-10-01", "2017-06-30"),
    "2017-18": ("2017-10-01", "2018-06-30"),
    "2018-19": ("2018-10-01", "2019-06-30"),
    "2019-20": ("2019-10-01", "2020-10-15"),  # 泡泡总决赛 2020-10-11
    "2020-21": ("2020-12-01", "2021-07-31"),  # 延迟赛季
    "2021-22": ("2021-10-01", "2022-06-30"),
    "2022-23": ("2022-10-01", "2023-06-30"),
    "2023-24": ("2023-10-01", "2024-06-30"),
    "2024-25": ("2024-10-01", "2025-06-30"),
    "2025-26": ("2025-10-01", "2026-06-30"),
}

ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}


def fix_abbr(abbr: str) -> str:
    return ESPN_ABBR_FIX.get(abbr, abbr)


def month_ranges(start: str, end: str) -> list:
    """按月拆分日期区间 -> [(yyyymmdd, yyyymmdd), ...]"""
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    ranges = []
    cur = s
    while cur <= e:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = min(nxt - timedelta(days=1), e)
        ranges.append((cur.strftime("%Y%m%d"), month_end.strftime("%Y%m%d")))
        cur = nxt
    return ranges


def fetch_month(dates: str, retries: int = 3) -> list:
    """抓取一个日期区间的比赛事件（失败自动重试）"""
    for attempt in range(retries):
        try:
            r = requests.get(
                SCOREBOARD,
                params={"dates": dates, "limit": 1000},
                proxies={"https": PROXY, "http": PROXY},
                timeout=40,
            )
            if r.status_code == 200:
                return r.json().get("events", [])
            logger.warning(f"  scoreboard {dates} HTTP {r.status_code} (attempt {attempt + 1})")
        except Exception as e:
            logger.warning(f"  scoreboard {dates} 失败 (attempt {attempt + 1}): {e}")
        time.sleep(2 * (attempt + 1))
    logger.error(f"  scoreboard {dates} 最终失败")
    return []


def parse_event(ev: dict, abbr_map: dict):
    """解析一个 ESPN 比赛事件 -> 结构化 dict 或 None"""
    try:
        comp = ev.get("competitions", [{}])[0]
        status_type = (comp.get("status") or {}).get("type", {})
        if status_type.get("completed") is not True:
            return None
        season_year = int((ev.get("season") or {}).get("year", 0))
        if not season_year:
            return None
        season_type = (ev.get("season") or {}).get("type", 2)
        if season_type == 1:  # 季前赛，跳过
            return None
        season = f"{season_year - 1}-{str(season_year)[-2:]}"
        # ESPN 日期是 UTC: 美东/太平洋晚场比赛会显示为次日。
        # 美国当地比赛最早 12:00 ET (17:00 UTC) 开始，UTC 时刻 < 9 的都属前一天晚上。
        ev_date = str(ev.get("date", ""))
        utc_dt = datetime.fromisoformat(ev_date.replace("Z", "+00:00"))
        game_date = utc_dt.date()
        if utc_dt.hour < 9:
            game_date = game_date - timedelta(days=1)

        home = away = None
        for c in comp.get("competitors", []):
            abbr = fix_abbr(str((c.get("team") or {}).get("abbreviation", "")))
            tid = abbr_map.get(abbr)
            score = c.get("score")
            try:
                score = int(float(score))
            except (TypeError, ValueError):
                return None
            if c.get("homeAway") == "home":
                home = (tid, score)
            else:
                away = (tid, score)

        if not home or not away or home[0] is None or away[0] is None:
            return None

        return {
            "espn_id": str(ev.get("id", "")),
            "season": season,
            "game_date": str(game_date),
            "home_team_id": home[0],
            "away_team_id": away[0],
            "home_score": home[1],
            "away_score": away[1],
            "is_playoff": 1 if season_type == 3 else 0,
        }
    except Exception as e:
        logger.debug(f"  事件解析失败: {e}")
        return None


def collect_events(refresh_cache: bool = False) -> dict:
    """收集全部 10 赛季事件: {season: {key: event}}，key = (date, home, away) 的字符串"""
    if not refresh_cache and CACHE_FILE.exists():
        cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if set(cached.keys()) == set(SEASON_RANGES.keys()):
            logger.info(f"使用缓存事件数据 {CACHE_FILE}")
            return cached

    with SessionLocal() as db:
        abbr_map = {t.abbreviation: t.team_id for t in db.query(Team).all()}

    all_events = {}
    for season, (start, end) in SEASON_RANGES.items():
        logger.info(f"[{season}] 抓取比赛 ({start} ~ {end}) ...")
        season_events = {}
        for d1, d2 in month_ranges(start, end):
            events = fetch_month(f"{d1}-{d2}")
            for ev in events:
                parsed = parse_event(ev, abbr_map)
                if parsed:
                    key = f"{parsed['game_date']}|{parsed['home_team_id']}|{parsed['away_team_id']}"
                    season_events[key] = parsed
            time.sleep(REQUEST_DELAY)
        logger.info(f"  共 {len(season_events)} 场")
        all_events[season] = season_events

    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(all_events, ensure_ascii=False), encoding="utf-8")
    return all_events


def reconcile(all_events: dict, dry_run: bool = False):
    """全局一次性对账：匹配修正 / 插入缺失 / 删除多余"""
    with SessionLocal() as db:
        all_games = db.query(GameRecord).all()
        id_index = {}
        db_index = {}
        for g in all_games:
            if g.nba_game_id:
                id_index.setdefault(g.nba_game_id, g)
            key = f"{g.game_date}|{g.home_team_id}|{g.away_team_id}"
            if key not in db_index:
                db_index[key] = g

        inserted = updated = matched_ok = score_fixed = 0
        matched_ids = set()

        for season, season_events in all_events.items():
            for key, ev in season_events.items():
                # 优先按 nba_game_id 匹配（同一场比赛日期被修正时按日期会匹配不上）
                g = id_index.get(f"espn_{ev['espn_id']}") or db_index.get(key)
                if g is None:
                    if not dry_run:
                        db.add(GameRecord(
                            nba_game_id=f"espn_{ev['espn_id']}",
                            season=ev["season"],
                            game_date=datetime.strptime(ev["game_date"], "%Y-%m-%d").date(),
                            game_type="Playoffs" if ev["is_playoff"] else "Regular Season",
                            home_team_id=ev["home_team_id"],
                            away_team_id=ev["away_team_id"],
                            home_score=ev["home_score"],
                            away_score=ev["away_score"],
                            home_win=1 if ev["home_score"] > ev["away_score"] else 0,
                            score_diff=ev["home_score"] - ev["away_score"],
                            total_score=ev["home_score"] + ev["away_score"],
                            is_playoff=ev["is_playoff"],
                            status="FINISHED",
                        ))
                        inserted += 1
                    continue

                matched_ids.add(g.game_id)
                changed = False
                if (g.home_score, g.away_score) != (ev["home_score"], ev["away_score"]):
                    g.home_score, g.away_score = ev["home_score"], ev["away_score"]
                    g.home_win = 1 if ev["home_score"] > ev["away_score"] else 0
                    g.score_diff = ev["home_score"] - ev["away_score"]
                    g.total_score = ev["home_score"] + ev["away_score"]
                    score_fixed += 1
                    changed = True
                if g.game_date != datetime.strptime(ev["game_date"], "%Y-%m-%d").date():
                    g.game_date = datetime.strptime(ev["game_date"], "%Y-%m-%d").date()
                    changed = True
                if (g.home_team_id, g.away_team_id) != (ev["home_team_id"], ev["away_team_id"]):
                    g.home_team_id, g.away_team_id = ev["home_team_id"], ev["away_team_id"]
                    changed = True
                if g.season != ev["season"]:
                    g.season = ev["season"]
                    changed = True
                if g.game_type not in ("Regular Season", "Playoffs") or (
                    (g.game_type == "Regular Season") == bool(ev["is_playoff"])
                ):
                    g.game_type = "Playoffs" if ev["is_playoff"] else "Regular Season"
                    g.is_playoff = ev["is_playoff"]
                    changed = True
                if changed:
                    updated += 1
                else:
                    matched_ok += 1

        # 删除 ESPN 没有的库内行（重复/多余数据）
        all_ids = {g.game_id for g in all_games}
        to_delete = all_ids - matched_ids
        if to_delete and not dry_run:
            deleted = db.query(GameRecord).filter(GameRecord.game_id.in_(to_delete)).delete(
                synchronize_session=False
            )
            logger.info(f"  删除库内多余比赛 {deleted} 场")

        # 清悬空的 series_star.key_game_id
        if not dry_run:
            valid_ids = {g.game_id for g in db.query(GameRecord.game_id).all()}
            dangling = 0
            for ss in db.query(SeriesStar).filter(SeriesStar.key_game_id.isnot(None)).all():
                if ss.key_game_id not in valid_ids:
                    ss.key_game_id = None
                    dangling += 1
            if dangling:
                logger.info(f"  清空悬空的 series_star.key_game_id {dangling} 条")

        if not dry_run:
            db.commit()

    logger.info("=" * 60)
    logger.info(
        f"对账完成: 新增 {inserted}, 修正 {updated} (含比分修正 {score_fixed}), 完全匹配 {matched_ok}"
    )
    logger.info("=" * 60)


def run(refresh_cache: bool = False, dry_run: bool = False):
    logger.info("=" * 60)
    logger.info("ESPN 10 赛季比赛记录采集 + 全局对账")
    logger.info("=" * 60)
    all_events = collect_events(refresh_cache=refresh_cache)
    if dry_run:
        total = sum(len(v) for v in all_events.values())
        logger.info(f"dry-run: 共 {total} 场事件，不写库")
        return
    reconcile(all_events)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-cache", action="store_true", help="强制重新抓取（忽略缓存）")
    parser.add_argument("--dry-run", action="store_true", help="只抓取统计，不写库")
    args = parser.parse_args()
    run(refresh_cache=args.refresh_cache, dry_run=args.dry_run)
