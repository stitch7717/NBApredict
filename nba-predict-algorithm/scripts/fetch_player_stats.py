"""
从 ESPN boxscore API 抓取球员赛季统计数据（轮换球员）
按日期批量获取，只保留场均 > 3 分钟的球员
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, Player, PlayerData, Team

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MIN_MINUTES = 3.0  # 轮换球员最低出场时间
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "player_stats_cache.json"

ctx = ssl.create_default_context()


def fetch_json(url: str, retries=2) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
    return {}


# 全局缓存 team abbreviation -> team_id
_ABBR_MAP = None


def get_abbr_map():
    global _ABBR_MAP
    if _ABBR_MAP is None:
        with SessionLocal() as db:
            teams = db.query(Team).all()
            _ABBR_MAP = {t.abbreviation: t.team_id for t in teams}
    return _ABBR_MAP


def get_espn_game_ids(date_str: str) -> dict:
    """获取某日期的 ESPN game_id -> (home_team_id, away_team_id) 映射"""
    url = f"{ESPN_SCOREBOARD}?dates={date_str}&limit=30"
    data = fetch_json(url)
    events = data.get("events", [])
    abbr_map = get_abbr_map()

    result = {}
    for e in events:
        espn_id = e.get("id")
        comp = e.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        if len(competitors) != 2 or not espn_id:
            continue

        home_id = away_id = None
        for c in competitors:
            abbr = c.get("team", {}).get("abbreviation", "")
            tid = abbr_map.get(abbr)
            if c.get("homeAway") == "home":
                home_id = tid
            else:
                away_id = tid

        if home_id and away_id:
            result[str(espn_id)] = (home_id, away_id)

    return result


def fetch_boxscore(espn_game_id: str) -> list:
    """获取某场比赛的球员数据"""
    url = f"{ESPN_SUMMARY}?event={espn_game_id}"
    data = fetch_json(url)
    bs = data.get("boxscore", {})
    players_section = bs.get("players", [])

    all_players = []
    for team_data in players_section:
        team_abbr = team_data.get("team", {}).get("abbreviation", "")
        for stat_group in team_data.get("statistics", []):
            labels = stat_group.get("labels", [])
            for ath_entry in stat_group.get("athletes", []):
                ath = ath_entry.get("athlete", {})
                espn_id = str(ath.get("id", ""))
                stats = ath_entry.get("stats", [])
                if not espn_id or not stats or len(stats) != len(labels):
                    continue

                all_players.append({
                    "espn_id": espn_id,
                    "name": ath.get("displayName", ""),
                    "team_abbr": team_abbr,
                    "stats": dict(zip(labels, stats)),
                })

    return all_players


def parse_stat(val, default=0):
    if not val or val == "-" or val == "DNP":
        return default
    try:
        return float(val)
    except:
        return default


def parse_fg(val):
    if not val or "-" not in str(val):
        return 0, 0, 0
    parts = str(val).split("-")
    try:
        made, att = int(parts[0]), int(parts[1])
        return made, att, round(made / att, 3) if att > 0 else 0
    except:
        return 0, 0, 0


def load_cache() -> dict:
    """加载缓存的球员统计数据"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(data: dict):
    """保存球员统计数据到缓存"""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def run():
    logger.info("=" * 50)
    logger.info("从 ESPN boxscore 抓取轮换球员统计数据")
    logger.info("=" * 50)

    target_season = sys.argv[1] if len(sys.argv) > 1 else "2025-26"
    logger.info(f"目标赛季: {target_season}")

    # 获取比赛日期
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED",
            GameRecord.season == target_season,
        ).all()
        dates = sorted(set(g.game_date.strftime("%Y%m%d") for g in games))

    logger.info(f"共 {len(dates)} 个比赛日")

    # 加载已有球员映射
    with SessionLocal() as db:
        players = db.query(Player).all()
        espn_to_player = {p.nba_id: p for p in players}
    logger.info(f"数据库有 {len(espn_to_player)} 名球员")

    # 加载缓存
    cache = load_cache()
    cached_dates = set(cache.get("_processed_dates", []))
    logger.info(f"缓存已有 {len(cached_dates)} 个日期的数据")

    # 球员统计聚合
    # key: espn_id, value: {season: {pts: [...], ...}}
    player_stats = defaultdict(lambda: defaultdict(lambda: {
        "games": 0, "minutes": [], "points": [], "rebounds": [],
        "assists": [], "steals": [], "blocks": [], "turnovers": [],
        "fg_made": [], "fg_att": [], "three_made": [], "three_att": [],
        "ft_made": [], "ft_att": [], "oreb": [], "dreb": [], "pf": [],
    }))

    # 从缓存恢复
    for espn_id, seasons in cache.items():
        if espn_id.startswith("_"):
            continue
        for season, stats in seasons.items():
            s = player_stats[espn_id][season]
            s["games"] = stats.get("games", 0)
            for k in ["minutes", "points", "rebounds", "assists", "steals",
                       "blocks", "turnovers", "fg_made", "fg_att",
                       "three_made", "three_att", "ft_made", "ft_att",
                       "oreb", "dreb", "pf"]:
                s[k] = stats.get(k, [])

    # 处理新日期
    new_dates = [d for d in dates if d not in cached_dates]
    logger.info(f"需要新抓取: {len(new_dates)} 个日期")

    processed = 0
    failed = 0
    start_time = time.time()

    for i, date_str in enumerate(new_dates):
        game_ids = get_espn_game_ids(date_str)
        if not game_ids:
            cached_dates.add(date_str)
            continue

        for espn_id, (home_tid, away_tid) in game_ids.items():
            players_data = fetch_boxscore(espn_id)
            if not players_data:
                failed += 1
                continue

            for pd in players_data:
                espn_pid = pd["espn_id"]
                stats = pd["stats"]
                s = player_stats[espn_pid][target_season]
                s["games"] += 1
                s["minutes"].append(parse_stat(stats.get("MIN")))
                s["points"].append(parse_stat(stats.get("PTS")))
                s["rebounds"].append(parse_stat(stats.get("REB")))
                s["assists"].append(parse_stat(stats.get("AST")))
                s["steals"].append(parse_stat(stats.get("STL")))
                s["blocks"].append(parse_stat(stats.get("BLK")))
                s["turnovers"].append(parse_stat(stats.get("TO")))
                s["oreb"].append(parse_stat(stats.get("OREB")))
                s["dreb"].append(parse_stat(stats.get("DREB")))
                s["pf"].append(parse_stat(stats.get("PF")))

                fg_m, fg_a, _ = parse_fg(stats.get("FG"))
                s["fg_made"].append(fg_m)
                s["fg_att"].append(fg_a)
                t_m, t_a, _ = parse_fg(stats.get("3PT"))
                s["three_made"].append(t_m)
                s["three_att"].append(t_a)
                ft_m, ft_a, _ = parse_fg(stats.get("FT"))
                s["ft_made"].append(ft_m)
                s["ft_att"].append(ft_a)

            processed += 1

        cached_dates.add(date_str)

        # 每 20 个日期保存一次缓存
        if (i + 1) % 20 == 0:
            cache_data = {"_processed_dates": list(cached_dates)}
            for pid, seasons in player_stats.items():
                cache_data[pid] = {}
                for season, s in seasons.items():
                    cache_data[pid][season] = {k: v for k, v in s.items()}
            save_cache(cache_data)

            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed
            remaining = (len(new_dates) - i - 1) / max(speed, 0.01)
            logger.info(f"  进度: {i+1}/{len(new_dates)}, "
                        f"已处理 {processed} 场, "
                        f"速度 {speed:.1f} 日期/秒, "
                        f"剩余约 {remaining/60:.0f} 分钟")

    # 保存最终缓存
    cache_data = {"_processed_dates": list(cached_dates)}
    for pid, seasons in player_stats.items():
        cache_data[pid] = {}
        for season, s in seasons.items():
            cache_data[pid][season] = {k: v for k, v in s.items()}
    save_cache(cache_data)

    logger.info(f"抓取完成: {processed} 场成功, {failed} 场失败")
    logger.info(f"球员数据条目: {sum(len(s) for s in player_stats.values())}")

    # 写入数据库
    with SessionLocal() as db:
        # 清除目标赛季旧数据
        old_count = db.query(PlayerData).filter(PlayerData.season == target_season).count()
        if old_count > 0:
            db.query(PlayerData).filter(PlayerData.season == target_season).delete()
            db.commit()
            logger.info(f"已清除 {old_count} 条旧数据")

        added = 0
        skipped_no_player = 0
        skipped_low_min = 0

        def avg(lst):
            vals = [v for v in lst if v > 0]
            return round(sum(vals) / len(vals), 1) if vals else 0

        def avg_all(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0

        for espn_pid, seasons in player_stats.items():
            player = espn_to_player.get(espn_pid)
            if not player:
                skipped_no_player += 1
                continue

            for season, s in seasons.items():
                gp = s["games"]
                if gp == 0:
                    continue

                mpg = avg_all(s["minutes"])
                if mpg < MIN_MINUTES:
                    skipped_low_min += 1
                    continue

                ppg = avg_all(s["points"])
                fg_m = avg_all(s["fg_made"])
                fg_a = avg_all(s["fg_att"])
                three_m = avg_all(s["three_made"])
                three_a = avg_all(s["three_att"])
                ft_m = avg_all(s["ft_made"])
                ft_a = avg_all(s["ft_att"])

                ts_denom = 2 * (fg_a + 0.44 * ft_a)

                pd_record = PlayerData(
                    player_id=player.player_id,
                    season=season,
                    team_id=player.team_id,
                    games_played=gp,
                    games_started=0,
                    minutes_per_game=mpg,
                    points_per_game=ppg,
                    rebounds_per_game=avg_all(s["rebounds"]),
                    assists_per_game=avg_all(s["assists"]),
                    steals_per_game=avg_all(s["steals"]),
                    blocks_per_game=avg_all(s["blocks"]),
                    turnovers_per_game=avg_all(s["turnovers"]),
                    fg_made_per_game=fg_m,
                    fg_attempted_per_game=fg_a,
                    fg_percentage=round(fg_m / fg_a, 3) if fg_a > 0 else 0,
                    three_made_per_game=three_m,
                    three_attempted_per_game=three_a,
                    three_percentage=round(three_m / three_a, 3) if three_a > 0 else 0,
                    ft_made_per_game=ft_m,
                    ft_attempted_per_game=ft_a,
                    ft_percentage=round(ft_m / ft_a, 3) if ft_a > 0 else 0,
                    per=0,
                    true_shooting_pct=round(ppg / ts_denom, 3) if ts_denom > 0 else 0,
                    usage_rate=0,
                    win_shares=0,
                    bpm=0,
                    vorp=0,
                    isolation_pct=0,
                    pick_roll_pct=0,
                    spot_up_pct=0,
                    post_up_pct=0,
                    points_std=0,
                    points_cv=0,
                )
                db.add(pd_record)
                added += 1

        db.commit()

        logger.info("=" * 50)
        logger.info(f"写入 PlayerData: {added}")
        logger.info(f"跳过(无匹配球员): {skipped_no_player}")
        logger.info(f"跳过(出场时间 < {MIN_MINUTES}分钟): {skipped_low_min}")
        logger.info(f"球员总数: {db.query(Player).count()}")
        logger.info(f"PlayerData 总数: {db.query(PlayerData).count()}")
        logger.info("=" * 50)


if __name__ == "__main__":
    run()
