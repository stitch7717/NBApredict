"""
从缓存重新聚合球员数据（修正 stats 解析路径）
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import PlayerData
from sqlalchemy import text

ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}


def fix_abbr(abbr):
    return ESPN_ABBR_FIX.get(abbr, abbr)


def parse_fg(val):
    if isinstance(val, (int, float)):
        return val, val
    if not val or "-" not in str(val):
        return 0, 0
    parts = str(val).split("-")
    try:
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0


def parse_num(val):
    if isinstance(val, (int, float)):
        return float(val)
    if not val:
        return 0
    try:
        return float(val)
    except:
        return 0


def parse_minutes(val):
    if isinstance(val, (int, float)):
        return float(val)
    if not val:
        return 0
    val = str(val)
    if ":" in val:
        parts = val.split(":")
        try:
            return int(parts[0]) + int(parts[1]) / 60
        except:
            return 0
    try:
        return float(val)
    except:
        return 0


def reaggregate():
    logger.info("=" * 60)
    logger.info("从缓存重新聚合球员数据（修正解析）")
    logger.info("=" * 60)

    # 加载缓存
    cache_file = Path(__file__).resolve().parent.parent / "data" / "espn_cache" / "boxscore_cache.json"
    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)
    logger.info(f"缓存条目: {len(cache)}")

    db = SessionLocal()
    try:
        # 获取球队映射
        teams = db.execute(text("SELECT team_id, abbreviation FROM team")).fetchall()
        abbr_to_id = {row[1]: row[0] for row in teams}

        # 获取球员映射
        result = db.execute(text("SELECT player_name, player_id FROM player"))
        name_to_pid = {row[0]: row[1] for row in result}
        logger.info(f"球员映射: {len(name_to_pid)}")

        # 获取比赛赛季映射
        game_records = db.execute(text("""
            SELECT nba_game_id, season FROM game_record
            WHERE status = 'FINISHED' AND nba_game_id LIKE 'espn_%'
        """)).fetchall()
        game_season = {row[0].replace("espn_", ""): row[1] for row in game_records}
        logger.info(f"比赛记录: {len(game_season)}")

        # 按球员+赛季聚合
        player_games = defaultdict(lambda: defaultdict(list))
        processed = 0

        for game_id, boxscore in cache.items():
            season = game_season.get(game_id)
            if not season:
                continue
            if not isinstance(boxscore, list):
                continue

            for team_data in boxscore:
                team_abbr = fix_abbr(team_data.get("team_abbr", ""))
                for p in team_data.get("players", []):
                    name = p.get("name", "")
                    stats = p.get("stats", {})
                    if not name or not stats:
                        continue

                    minutes = parse_minutes(stats.get("MIN", 0))
                    if minutes < 1:
                        continue

                    fgm, fga = parse_fg(stats.get("FG", "0-0"))
                    fg3m, fg3a = parse_fg(stats.get("3PT", "0-0"))
                    ftm, fta = parse_fg(stats.get("FT", "0-0"))

                    player_games[name][season].append({
                        "min": minutes,
                        "pts": parse_num(stats.get("PTS", 0)),
                        "reb": parse_num(stats.get("REB", 0)),
                        "ast": parse_num(stats.get("AST", 0)),
                        "stl": parse_num(stats.get("STL", 0)),
                        "blk": parse_num(stats.get("BLK", 0)),
                        "tov": parse_num(stats.get("TO", 0)),
                        "fgm": fgm,
                        "fga": fga,
                        "fg3m": fg3m,
                        "fg3a": fg3a,
                        "ftm": ftm,
                        "fta": fta,
                        "oreb": parse_num(stats.get("OREB", 0)),
                        "dreb": parse_num(stats.get("DREB", 0)),
                    })

            processed += 1

        logger.info(f"处理比赛: {processed}")
        logger.info(f"球员-赛季组合: {sum(len(v) for v in player_games.values())}")

        # 聚合赛季统计
        season_stats = {}
        for player_name, seasons in player_games.items():
            for season, games_list in seasons.items():
                gp = len(games_list)
                if gp < 3:
                    continue

                def avg_all(key):
                    vals = [g.get(key, 0) for g in games_list]
                    return round(sum(vals) / len(vals), 1) if vals else 0.0

                mpg = avg_all("min")
                if mpg < 3.0:
                    continue

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

                ts_pct = round((avg_all("pts") / 2) / max(fgm + 0.44 * fta, 0.001), 3) if (fgm + 0.44 * fta) > 0 else 0
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
                    "points_std": pts_std,
                    "points_cv": pts_cv,
                }

        logger.info(f"聚合赛季统计: {len(season_stats)} 条")

        # 写入数据库（只补充缺失的）
        added = 0
        skipped = 0
        for (player_name, season), stats in season_stats.items():
            pid = name_to_pid.get(player_name)
            if not pid:
                skipped += 1
                continue

            # 检查是否已存在
            existing = db.execute(text("""
                SELECT id FROM player_data WHERE player_id = :pid AND season = :season
            """), {"pid": pid, "season": season}).fetchone()

            if existing:
                continue

            pd = PlayerData(
                player_id=pid,
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
                usage_rate=0,
                assist_pct=0,
                rebound_pct=0,
                steal_pct=0,
                block_pct=0,
                turnover_pct=0,
                points_std=stats["points_std"],
                points_cv=stats["points_cv"],
                per=0, win_shares=0, bpm=0, vorp=0,
                isolation_pct=0, pick_roll_pct=0, spot_up_pct=0, post_up_pct=0,
                offensive_rating=0, defensive_rating=0, net_rating=0,
            )
            db.add(pd)
            added += 1

        db.commit()
        logger.info(f"新增 PlayerData: {added}, 跳过(无匹配): {skipped}")

        # 验证
        result = db.execute(text("SELECT COUNT(*) FROM player_data"))
        total_pd = result.scalar()

        result = db.execute(text("SELECT COUNT(DISTINCT player_id) FROM player_data"))
        players_with_data = result.scalar()

        result = db.execute(text("SELECT season, COUNT(*) FROM player_data GROUP BY season ORDER BY season"))
        print(f"\n=== 最终结果 ===")
        print(f"球员赛季数据: {total_pd}, 有数据球员: {players_with_data}")
        print("各赛季:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    finally:
        db.close()


if __name__ == "__main__":
    reaggregate()
