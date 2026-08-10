"""
修复缺失球员：删除假数据，添加真实 ESPN 球员，重新聚合
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData
from sqlalchemy import text

ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}


def fix_abbr(abbr):
    return ESPN_ABBR_FIX.get(abbr, abbr)


def fix():
    db = SessionLocal()
    try:
        # 1. 删除没有数据的假球员
        logger.info("=== Step 1: 删除假球员 ===")
        result = db.execute(text("""
            SELECT player_id, player_name FROM player p
            WHERE NOT EXISTS (SELECT 1 FROM player_data pd WHERE pd.player_id = p.player_id)
        """))
        fake_players = [(row[0], row[1]) for row in result]
        logger.info(f"假球员: {len(fake_players)}")

        for pid, name in fake_players:
            db.execute(text("DELETE FROM player WHERE player_id = :pid"), {"pid": pid})

        db.commit()
        logger.info(f"已删除 {len(fake_players)} 个假球员")

        # 2. 从 ESPN 缓存获取所有真实球员名
        logger.info("\\n=== Step 2: 添加缺失的 ESPN 球员 ===")
        cache_file = Path(__file__).resolve().parent.parent / "data" / "espn_cache" / "boxscore_cache.json"
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)

        # 获取球队映射
        teams = db.execute(text("SELECT team_id, abbreviation FROM team")).fetchall()
        abbr_to_id = {row[1]: row[0] for row in teams}

        # 获取现有球员
        result = db.execute(text("SELECT player_name, player_id FROM player"))
        existing_players = {row[0]: row[1] for row in result}

        # 从缓存中提取所有球员+球队
        espn_players = {}  # name -> team_abbr
        for game_id, boxscore in cache.items():
            if not isinstance(boxscore, list):
                continue
            for team_data in boxscore:
                team_abbr = fix_abbr(team_data.get("team_abbr", ""))
                for p in team_data.get("players", []):
                    name = p.get("name", "")
                    if name and name not in espn_players:
                        espn_players[name] = team_abbr

        logger.info(f"ESPN 球员: {len(espn_players)}, DB 球员: {len(existing_players)}")

        # 添加缺失球员（使用原始 SQL 避免 ORM 约束）
        added = 0
        # 获取最大 nba_id
        result = db.execute(text("SELECT MAX(CAST(nba_id AS UNSIGNED)) FROM player"))
        max_nba_id = result.scalar() or 9000000

        for name, team_abbr in espn_players.items():
            if name in existing_players:
                continue

            team_id = abbr_to_id.get(team_abbr, 0)
            max_nba_id += 1
            db.execute(text("""
                INSERT INTO player (nba_id, player_name, player_name_en, position, team_id, status, injury_status, all_star_count)
                VALUES (:nba_id, :name, :name_en, :pos, :team_id, 1, 'HEALTHY', 0)
            """), {
                "nba_id": str(max_nba_id),
                "name": name,
                "name_en": name,
                "pos": "",
                "team_id": team_id,
            })
            added += 1

        db.commit()
        logger.info(f"新增球员: {added}")

        # 3. 重新获取球员映射
        result = db.execute(text("SELECT player_name, player_id FROM player"))
        name_to_pid = {row[0]: row[1] for row in result}
        logger.info(f"当前球员总数: {len(name_to_pid)}")

        # 4. 从缓存重新聚合球员赛季数据（补充新球员的数据）
        logger.info("\\n=== Step 3: 聚合新球员数据 ===")
        game_records = db.execute(text("""
            SELECT nba_game_id, season FROM game_record
            WHERE status = 'FINISHED' AND nba_game_id LIKE 'espn_%'
        """)).fetchall()
        game_season = {row[0].replace("espn_", ""): row[1] for row in game_records}

        # 按球员+赛季聚合
        player_games = defaultdict(lambda: defaultdict(list))
        for game_id, boxscore in cache.items():
            season = game_season.get(game_id)
            if not season:
                continue
            if not isinstance(boxscore, list):
                continue

            for team_data in boxscore:
                for p in team_data.get("players", []):
                    name = p.get("name", "")
                    if not name or p.get("min", 0) < 1:
                        continue
                    player_games[name][season].append(p)

        # 聚合并写入
        added_pd = 0
        for player_name, seasons in player_games.items():
            pid = name_to_pid.get(player_name)
            if not pid:
                continue

            for season, games_list in seasons.items():
                # 检查是否已有数据
                existing = db.execute(text("""
                    SELECT id FROM player_data WHERE player_id = :pid AND season = :season
                """), {"pid": pid, "season": season}).fetchone()

                if existing:
                    continue

                gp = len(games_list)
                if gp < 3:
                    continue

                def avg_all(key):
                    vals = [g.get(key, 0) for g in games_list]
                    return round(sum(vals) / len(vals), 1) if vals else 0.0

                mpg = avg_all("min")
                if mpg < 3.0:
                    continue

                fgm = avg_all("fgm")
                fga = avg_all("fga")
                fg3m = avg_all("fg3m")
                fg3a = avg_all("fg3a")
                ftm = avg_all("ftm")
                fta = avg_all("fta")

                ts_pct = round((avg_all("pts") / 2) / max(fgm + 0.44 * fta, 0.001), 3) if (fgm + 0.44 * fta) > 0 else 0
                efg_pct = round((fgm + 0.5 * fg3m) / max(fga, 0.001), 3) if fga > 0 else 0

                pd = PlayerData(
                    player_id=pid,
                    season=season,
                    team_id=0,
                    games_played=gp,
                    games_started=0,
                    minutes_per_game=mpg,
                    points_per_game=avg_all("pts"),
                    rebounds_per_game=avg_all("reb"),
                    assists_per_game=avg_all("ast"),
                    steals_per_game=avg_all("stl"),
                    blocks_per_game=avg_all("blk"),
                    turnovers_per_game=avg_all("tov"),
                    fg_made_per_game=fgm,
                    fg_attempted_per_game=fga,
                    fg_percentage=round(fgm / max(fga, 0.001), 3),
                    three_made_per_game=fg3m,
                    three_attempted_per_game=fg3a,
                    three_percentage=round(fg3m / max(fg3a, 0.001), 3),
                    ft_made_per_game=ftm,
                    ft_attempted_per_game=fta,
                    ft_percentage=round(ftm / max(fta, 0.001), 3),
                    true_shooting_pct=ts_pct,
                    effective_fg_pct=efg_pct,
                    usage_rate=0,
                    assist_pct=0,
                    rebound_pct=0,
                    steal_pct=0,
                    block_pct=0,
                    turnover_pct=0,
                    points_std=0,
                    points_cv=0,
                    per=0, win_shares=0, bpm=0, vorp=0,
                    isolation_pct=0, pick_roll_pct=0, spot_up_pct=0, post_up_pct=0,
                    offensive_rating=0, defensive_rating=0, net_rating=0,
                )
                db.add(pd)
                added_pd += 1

        db.commit()
        logger.info(f"新增 PlayerData: {added_pd}")

        # 5. 验证
        result = db.execute(text("SELECT COUNT(*) FROM player"))
        total_players = result.scalar()

        result = db.execute(text("SELECT COUNT(*) FROM player_data"))
        total_pd = result.scalar()

        result = db.execute(text("SELECT season, COUNT(*) FROM player_data GROUP BY season ORDER BY season"))
        print("\\n=== 最终结果 ===")
        print(f"球员: {total_players}, 球员赛季数据: {total_pd}")
        print("各赛季:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    finally:
        db.close()


if __name__ == "__main__":
    fix()
