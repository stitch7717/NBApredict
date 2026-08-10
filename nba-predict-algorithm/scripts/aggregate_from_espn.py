"""
从 ESPN API 直接获取并聚合球员赛季数据
跳过已有数据的赛季，只补充缺失的
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, GameRecord
from sqlalchemy import text

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_DELAY = 1.2

ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fix_abbr(abbr):
    return ESPN_ABBR_FIX.get(abbr, abbr)


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return None


def parse_stat(val):
    """解析字符串统计值"""
    if isinstance(val, (int, float)):
        return val
    if not val or val == "":
        return 0
    try:
        return float(val)
    except:
        return 0


def parse_fg(val):
    """解析 '4-7' 格式的投篮数据，返回 (made, attempted)"""
    if isinstance(val, (int, float)):
        return val, val
    if not val or "-" not in str(val):
        return 0, 0
    parts = str(val).split("-")
    try:
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0


def parse_minutes(val):
    """解析分钟数"""
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


def fetch_boxscore(espn_game_id):
    """获取比赛 boxscore 并解析球员数据"""
    url = f"{ESPN_SUMMARY}?event={espn_game_id}"
    data = fetch_json(url)
    if not data or "boxscore" not in data:
        return None

    result = []
    boxscore = data["boxscore"]

    if "players" not in boxscore:
        return None

    for team_data in boxscore["players"]:
        team_info = team_data.get("team", {})
        team_abbr = fix_abbr(team_info.get("abbreviation", ""))

        players = []
        for stat_group in team_data.get("statistics", []):
            labels = stat_group.get("labels", [])
            for athlete in stat_group.get("athletes", []):
                player_name = athlete.get("athlete", {}).get("displayName", "")
                stats = athlete.get("stats", [])

                stat_dict = {}
                for i, label in enumerate(labels):
                    if i < len(stats):
                        stat_dict[label] = stats[i]

                # 解析统计
                minutes = parse_minutes(stat_dict.get("MIN", 0))
                fgm, fga = parse_fg(stat_dict.get("FG", "0-0"))
                fg3m, fg3a = parse_fg(stat_dict.get("3PT", "0-0"))
                ftm, fta = parse_fg(stat_dict.get("FT", "0-0"))

                players.append({
                    "name": player_name,
                    "min": minutes,
                    "pts": parse_stat(stat_dict.get("PTS", 0)),
                    "reb": parse_stat(stat_dict.get("REB", 0)),
                    "ast": parse_stat(stat_dict.get("AST", 0)),
                    "stl": parse_stat(stat_dict.get("STL", 0)),
                    "blk": parse_stat(stat_dict.get("BLK", 0)),
                    "tov": parse_stat(stat_dict.get("TO", 0)),
                    "fgm": fgm,
                    "fga": fga,
                    "fg3m": fg3m,
                    "fg3a": fg3a,
                    "ftm": ftm,
                    "fta": fta,
                    "oreb": parse_stat(stat_dict.get("OREB", 0)),
                    "dreb": parse_stat(stat_dict.get("DREB", 0)),
                })

        result.append({"team_abbr": team_abbr, "players": players})

    return result


def aggregate_missing_seasons():
    """补充缺失赛季的球员数据"""
    logger.info("=" * 60)
    logger.info("从 ESPN API 补充缺失赛季的球员数据")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 检查已有数据
        result = db.execute(text("SELECT season, COUNT(*) FROM player_data GROUP BY season"))
        existing = {row[0]: row[1] for row in result}
        logger.info(f"已有数据: {existing}")

        # 需要补充的赛季
        target_seasons = ["2022-23", "2023-24"]
        missing = [s for s in target_seasons if s not in existing or existing[s] < 100]
        logger.info(f"需要补充: {missing}")

        if not missing:
            logger.info("所有赛季数据已完整")
            return

        # 获取球队映射
        teams = db.execute(text("SELECT team_id, abbreviation FROM team")).fetchall()
        abbr_to_id = {row[1]: row[0] for row in teams}

        # 获取球员映射
        players = db.execute(text("SELECT player_id, player_name FROM player")).fetchall()
        name_to_pid = {row[1]: row[0] for row in players}

        # 获取需要处理的比赛
        games = db.execute(text("""
            SELECT game_id, nba_game_id, season, game_date
            FROM game_record
            WHERE status = 'FINISHED' AND nba_game_id LIKE 'espn_%'
            AND season IN ({})
            ORDER BY game_date
        """.format(",".join(f"'{s}'" for s in missing)))).fetchall()

        logger.info(f"需要处理的比赛: {len(games)}")

        # 按球员+赛季聚合
        player_games = defaultdict(lambda: defaultdict(list))
        processed = 0
        errors = 0

        for i, game in enumerate(games):
            espn_id = game[1].replace("espn_", "")
            season = game[2]

            boxscore = fetch_boxscore(espn_id)
            if not boxscore:
                errors += 1
                if i % 100 == 0:
                    logger.info(f"  进度: {i}/{len(games)}, 成功: {processed}, 失败: {errors}")
                time.sleep(REQUEST_DELAY)
                continue

            for team_data in boxscore:
                for p in team_data["players"]:
                    if not p["name"] or p["min"] < 1:
                        continue
                    player_games[p["name"]][season].append(p)

            processed += 1
            if i % 50 == 0:
                logger.info(f"  进度: {i}/{len(games)}, 成功: {processed}, 失败: {errors}")

            time.sleep(REQUEST_DELAY)

        logger.info(f"处理完成: 成功 {processed}, 失败 {errors}")

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
                    "usage_rate": 0,
                    "assist_pct": 0,
                    "rebound_pct": 0,
                    "steal_pct": 0,
                    "block_pct": 0,
                    "turnover_pct": 0,
                    "points_std": pts_std,
                    "points_cv": pts_cv,
                }

        logger.info(f"聚合赛季统计: {len(season_stats)} 条")

        # 写入数据库
        added = 0
        skipped = 0
        for (player_name, season), stats in season_stats.items():
            player_id = name_to_pid.get(player_name)
            if not player_id:
                skipped += 1
                continue

            existing = db.execute(text("""
                SELECT id FROM player_data
                WHERE player_id = :pid AND season = :season
            """), {"pid": player_id, "season": season}).fetchone()

            if existing:
                continue

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
        logger.info(f"新增 PlayerData: {added}, 跳过(无匹配): {skipped}")

        # 验证
        result = db.execute(text("SELECT season, COUNT(*) FROM player_data GROUP BY season ORDER BY season"))
        print("\n=== 最终 player_data 分布 ===")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    finally:
        db.close()


if __name__ == "__main__":
    aggregate_missing_seasons()
