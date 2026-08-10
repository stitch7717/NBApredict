"""
从 boxscore 缓存重新聚合缺失赛季的球员数据
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, GameRecord
from sqlalchemy import text

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "espn_cache"
ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}


def fix_abbr(abbr):
    return ESPN_ABBR_FIX.get(abbr, abbr)


def get_team_abbr_map():
    db = SessionLocal()
    try:
        teams = db.execute(text("SELECT team_id, abbreviation FROM team")).fetchall()
        abbr_to_id = {row[1]: row[0] for row in teams}
        id_to_abbr = {row[0]: row[1] for row in teams}
        return abbr_to_id, id_to_abbr
    finally:
        db.close()


def get_espn_player_map():
    db = SessionLocal()
    try:
        players = db.execute(text("SELECT player_id, player_name FROM player")).fetchall()
        return {row[1]: row[0] for row in players}
    finally:
        db.close()


def process_boxscore(boxscore_data, abbr_to_id, id_to_abbr, game_record):
    """从 boxscore 提取球员数据"""
    players = []
    boxscore = boxscore_data if isinstance(boxscore_data, list) else []

    for team_data in boxscore:
        team_abbr = fix_abbr(team_data.get("team_abbr", ""))
        team_id = abbr_to_id.get(team_abbr)

        if not team_data.get("players"):
            continue

        for p in team_data["players"]:
            minutes = p.get("min", 0)
            if isinstance(minutes, str):
                try:
                    parts = minutes.split(":")
                    minutes = int(parts[0]) + int(parts[1]) / 60 if len(parts) == 2 else float(minutes)
                except:
                    minutes = 0

            players.append({
                "name": p.get("name", ""),
                "team_abbr": team_abbr,
                "team_id": team_id,
                "min": minutes,
                "pts": p.get("pts", 0),
                "reb": p.get("reb", 0),
                "ast": p.get("ast", 0),
                "stl": p.get("stl", 0),
                "blk": p.get("blk", 0),
                "tov": p.get("tov", 0),
                "fgm": p.get("fgm", 0),
                "fga": p.get("fga", 0),
                "fg3m": p.get("fg3m", 0),
                "fg3a": p.get("fg3a", 0),
                "ftm": p.get("ftm", 0),
                "fta": p.get("fta", 0),
                "oreb": p.get("oreb", 0),
                "dreb": p.get("dreb", 0),
                "pf": p.get("pf", 0),
            })

    return players


def aggregate_and_write():
    logger.info("=" * 60)
    logger.info("从缓存重新聚合缺失赛季的球员数据")
    logger.info("=" * 60)

    # 加载缓存
    cache_file = CACHE_DIR / "boxscore_cache.json"
    if not cache_file.exists():
        logger.error("缓存文件不存在")
        return

    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)
    logger.info(f"缓存条目: {len(cache)}")

    abbr_to_id, id_to_abbr = get_team_abbr_map()
    name_to_pid = get_espn_player_map()
    logger.info(f"球队映射: {len(abbr_to_id)} 支, 球员映射: {len(name_to_pid)} 名")

    db = SessionLocal()
    try:
        # 获取所有 game_record
        games = db.execute(text("""
            SELECT game_id, nba_game_id, season, game_date,
                   home_team_id, away_team_id
            FROM game_record
            WHERE status = 'FINISHED' AND nba_game_id LIKE 'espn_%'
            ORDER BY game_date
        """)).fetchall()

        logger.info(f"比赛记录: {len(games)}")

        # 按球员+赛季聚合
        player_games = defaultdict(lambda: defaultdict(list))
        processed = 0
        skipped = 0

        for game in games:
            espn_id = game[1].replace("espn_", "")
            season = game[2]

            if espn_id not in cache:
                skipped += 1
                continue

            boxscore = cache[espn_id]
            players = process_boxscore(boxscore, abbr_to_id, id_to_abbr, game)

            for p in players:
                if not p["name"] or p["min"] < 1:
                    continue
                player_games[p["name"]][season].append(p)

            processed += 1

        logger.info(f"处理: {processed}, 跳过(无缓存): {skipped}")
        logger.info(f"球员-赛季组合: {sum(len(v) for v in player_games.values())}")

        # 聚合赛季统计
        season_stats = {}
        for player_name, seasons in player_games.items():
            for season, games_list in seasons.items():
                gp = len(games_list)
                if gp < 3:
                    continue

                def avg(key):
                    vals = [g.get(key, 0) for g in games_list if g.get("min", 0) > 0]
                    return round(sum(vals) / len(vals), 1) if vals else 0.0

                def avg_all(key):
                    vals = [g.get(key, 0) for g in games_list]
                    return round(sum(vals) / len(vals), 1) if vals else 0.0

                mpg = avg_all("min")
                if mpg < 3.0:
                    continue

                # 标准差
                pts_list = [g.get("pts", 0) for g in games_list if g.get("min", 0) > 0]
                if len(pts_list) > 1:
                    pts_mean = sum(pts_list) / len(pts_list)
                    pts_std = round((sum((x - pts_mean) ** 2 for x in pts_list) / (len(pts_list) - 1)) ** 0.5, 1)
                    pts_cv = round(pts_std / max(pts_mean, 1), 3)
                else:
                    pts_std = 0.0
                    pts_cv = 0.0

                fgm = avg_all("fgm")
                fga = avg_all("fga")
                fg3m = avg_all("fg3m")
                fg3a = avg_all("fg3a")
                ftm = avg_all("ftm")
                fta = avg_all("fta")

                # TS% 计算
                ts_pct = round((avg_all("pts") / 2) / max(fgm + 0.44 * fta, 0.001), 3) if (fgm + 0.44 * fta) > 0 else 0

                # eFG% 计算
                efg_pct = round((fgm + 0.5 * fg3m) / max(fga, 0.001), 3) if fga > 0 else 0

                season_stats[(player_name, season)] = {
                    "games_played": gp,
                    "minutes_per_game": mpg,
                    "points_per_game": avg_all("pts"),
                    "rebounds_per_game": avg_all("reb"),
                    "assists_per_game": avg_all("ast"),
                    "steals_per_game": avg_all("stl"),
                    "blocks_per_game": avg_all("blk"),
                    "turnovers_per_game": avg_all("tov"),
                    "fg_made_per_game": fgm,
                    "fg_attempted_per_game": fga,
                    "fg_percentage": round(fgm / max(fga, 0.001), 3),
                    "three_made_per_game": fg3m,
                    "three_attempted_per_game": fg3a,
                    "three_percentage": round(fg3m / max(fg3a, 0.001), 3),
                    "ft_made_per_game": ftm,
                    "ft_attempted_per_game": fta,
                    "ft_percentage": round(ftm / max(fta, 0.001), 3),
                    "true_shooting_pct": ts_pct,
                    "effective_fg_pct": efg_pct,
                    "usage_rate": 0,  # 需要更复杂的计算
                    "assist_pct": 0,
                    "rebound_pct": 0,
                    "steal_pct": 0,
                    "block_pct": 0,
                    "turnover_pct": 0,
                    "points_std": pts_std,
                    "points_cv": pts_cv,
                }

        logger.info(f"聚合赛季统计: {len(season_stats)} 条")

        # 写入数据库 - 只补充缺失的
        added = 0
        skipped = 0
        for (player_name, season), stats in season_stats.items():
            player_id = name_to_pid.get(player_name)
            if not player_id:
                skipped += 1
                continue

            # 检查是否已存在
            existing = db.execute(text("""
                SELECT id FROM player_data
                WHERE player_id = :pid AND season = :season
            """), {"pid": player_id, "season": season}).fetchone()

            if existing:
                continue  # 已存在，跳过

            pd = PlayerData(
                player_id=player_id,
                season=season,
                team_id=0,
                games_played=stats["games_played"],
                games_started=0,
                minutes_per_game=stats["minutes_per_game"],
                points_per_game=stats["points_per_game"],
                rebounds_per_game=stats["rebounds_per_game"],
                assists_per_game=stats["assists_per_game"],
                steals_per_game=stats["steals_per_game"],
                blocks_per_game=stats["blocks_per_game"],
                turnovers_per_game=stats["turnovers_per_game"],
                fg_made_per_game=stats["fg_made_per_game"],
                fg_attempted_per_game=stats["fg_attempted_per_game"],
                fg_percentage=stats["fg_percentage"],
                three_made_per_game=stats["three_made_per_game"],
                three_attempted_per_game=stats["three_attempted_per_game"],
                three_percentage=stats["three_percentage"],
                ft_made_per_game=stats["ft_made_per_game"],
                ft_attempted_per_game=stats["ft_attempted_per_game"],
                ft_percentage=stats["ft_percentage"],
                true_shooting_pct=stats["true_shooting_pct"],
                effective_fg_pct=stats["effective_fg_pct"],
                usage_rate=stats["usage_rate"],
                assist_pct=stats["assist_pct"],
                rebound_pct=stats["rebound_pct"],
                steal_pct=stats["steal_pct"],
                block_pct=stats["block_pct"],
                turnover_pct=stats["turnover_pct"],
                points_std=stats["points_std"],
                points_cv=stats["points_cv"],
                per=0, win_shares=0, bpm=0, vorp=0,
                isolation_pct=0, pick_roll_pct=0, spot_up_pct=0, post_up_pct=0,
                offensive_rating=0, defensive_rating=0, net_rating=0,
            )
            db.add(pd)
            added += 1

        db.commit()
        logger.info(f"新增 PlayerData: {added}, 跳过(无匹配球员): {skipped}")

        # 验证
        result = db.execute(text("SELECT season, COUNT(*) FROM player_data GROUP BY season ORDER BY season"))
        print("\n=== 最终 player_data 分布 ===")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    finally:
        db.close()


if __name__ == "__main__":
    aggregate_and_write()
