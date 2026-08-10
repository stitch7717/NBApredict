"""
NBA数据导入脚本
从NBA Stats API获取球员和球队数据并写入数据库
"""
import sys
import os
import json
import random
from datetime import date, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from loguru import logger
from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.db.models import Base, Player, PlayerData, Team, TeamData, GameRecord
from config.settings import NBA_STATS_CONFIG, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# NBA Stats API headers
HEADERS = NBA_STATS_CONFIG["headers"]
TIMEOUT = NBA_STATS_CONFIG["timeout"]
BASE_URL = NBA_STATS_CONFIG["base_url"]

# 2024-25赛季球队映射 (nba_id -> team表中的team_id)
TEAM_MAP = {
    1610612737: 1, 1610612738: 2, 1610612751: 3, 1610612766: 4,
    1610612741: 5, 1610612739: 6, 1610612742: 7, 1610612743: 8,
    1610612765: 9, 1610612744: 10, 1610612745: 11, 1610612754: 12,
    1610612746: 13, 1610612747: 14, 1610612763: 15, 1610612748: 16,
    1610612749: 17, 1610612750: 18, 1610612740: 19, 1610612752: 20,
    1610612760: 21, 1610612753: 22, 1610612755: 23, 1610612756: 24,
    1610612757: 25, 1610612758: 26, 1610612759: 27, 1610612761: 28,
    1610612762: 29, 1610612764: 30,
}


def fetch_api(endpoint: str, params: dict = None) -> dict:
    """从NBA Stats API获取数据"""
    url = f"{BASE_URL}/{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"API请求失败: {endpoint} - {e}")
        return None


def fetch_players():
    """获取当前赛季球员列表"""
    logger.info("获取球员列表...")
    data = fetch_api("commonallplayers", {
        "LeagueID": "00",
        "Season": "2024-25",
        "IsOnlyCurrentSeason": "1"
    })
    if not data:
        return []

    players = []
    for row in data["resultSets"][0]["rowSet"]:
        nba_id = str(row[0])
        name = row[2]
        team_nba_id = row[7] if row[7] else None
        team_id = TEAM_MAP.get(team_nba_id)
        players.append({
            "nba_id": nba_id,
            "player_name": name,
            "player_name_en": name,
            "team_id": team_id,
        })
    logger.info(f"获取到 {len(players)} 名球员")
    return players


def fetch_player_stats():
    """获取球员赛季数据"""
    logger.info("获取球员赛季数据...")
    data = fetch_api("leaguedashplayerstats", {
        "Conference": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "GameScope": "",
        "GameSegment": "",
        "Height": "",
        "ISTRound": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Base",
        "Month": "0",
        "OpponentTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PaceAdjust": "N",
        "PerMode": "PerGame",
        "Period": "0",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "Rank": "N",
        "Season": "2024-25",
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "TwoWay": "0",
        "VsConference": "",
        "VsDivision": "",
    })
    if not data:
        return []

    stats = []
    for row in data["resultSets"][0]["rowSet"]:
        nba_id = str(row[0])
        name = row[1]
        gp = row[4] or 0
        gs = row[5] or 0
        min_pg = row[6] or 0
        pts = row[26] or 0
        reb = row[18] or 0
        ast = row[19] or 0
        stl = row[20] or 0
        blk = row[21] or 0
        tov = row[22] or 0
        fg_made = row[7] or 0
        fg_att = row[8] or 0
        fg_pct = row[9] or 0
        three_made = row[10] or 0
        three_att = row[11] or 0
        three_pct = row[12] or 0
        ft_made = row[13] or 0
        ft_att = row[14] or 0
        ft_pct = row[15] or 0

        stats.append({
            "nba_id": nba_id,
            "player_name": name,
            "games_played": int(gp),
            "games_started": int(gs),
            "minutes_per_game": round(float(min_pg), 1),
            "points_per_game": round(float(pts), 1),
            "rebounds_per_game": round(float(reb), 1),
            "assists_per_game": round(float(ast), 1),
            "steals_per_game": round(float(stl), 1),
            "blocks_per_game": round(float(blk), 1),
            "turnovers_per_game": round(float(tov), 1),
            "fg_made_per_game": round(float(fg_made), 1),
            "fg_attempted_per_game": round(float(fg_att), 1),
            "fg_percentage": round(float(fg_pct), 3),
            "three_made_per_game": round(float(three_made), 1),
            "three_attempted_per_game": round(float(three_att), 1),
            "three_percentage": round(float(three_pct), 3),
            "ft_made_per_game": round(float(ft_made), 1),
            "ft_attempted_per_game": round(float(ft_att), 1),
            "ft_percentage": round(float(ft_pct), 3),
        })
    logger.info(f"获取到 {len(stats)} 名球员赛季数据")
    return stats


def fetch_team_stats():
    """获取球队赛季数据"""
    logger.info("获取球队赛季数据...")
    data = fetch_api("leaguedashteamstats", {
        "Conference": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "GameScope": "",
        "GameSegment": "",
        "ISTRound": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Base",
        "Month": "0",
        "OpponentTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PaceAdjust": "N",
        "PerMode": "PerGame",
        "Period": "0",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "Rank": "N",
        "Season": "2024-25",
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "TwoWay": "0",
        "VsConference": "",
        "VsDivision": "",
    })
    if not data:
        return []

    stats = []
    for row in data["resultSets"][0]["rowSet"]:
        nba_team_id = row[0]
        team_id = TEAM_MAP.get(nba_team_id)
        if not team_id:
            continue

        stats.append({
            "team_id": team_id,
            "nba_team_id": str(nba_team_id),
            "wins": int(row[3] or 0),
            "losses": int(row[4] or 0),
            "win_percentage": round(float(row[5] or 0), 3),
            "fg_percentage": round(float(row[9] or 0), 3),
            "three_percentage": round(float(row[12] or 0), 3),
            "ft_percentage": round(float(row[15] or 0), 3),
            "rebounds_per_game": round(float(row[18] or 0), 1),
            "assists_per_game": round(float(row[19] or 0), 1),
            "turnovers_per_game": round(float(row[20] or 0), 1),
            "steals_per_game": round(float(row[21] or 0), 1),
            "blocks_per_game": round(float(row[22] or 0), 1),
            "points_per_game": round(float(row[23] or 0), 1),
            "opponent_points": round(float(row[24] or 0), 1),
        })
    logger.info(f"获取到 {len(stats)} 支球队赛季数据")
    return stats


def insert_players(players: list):
    """插入球员数据"""
    logger.info("写入球员数据...")
    with SessionLocal() as db:
        for p in players:
            exists = db.query(Player).filter(Player.nba_id == p["nba_id"]).first()
            if exists:
                continue
            player = Player(
                nba_id=p["nba_id"],
                player_name=p["player_name"],
                player_name_en=p.get("player_name_en"),
                team_id=p.get("team_id"),
                status=1,
            )
            db.add(player)
        db.commit()
    logger.info("球员数据写入完成")


def insert_player_stats(stats: list, season: str = "2024-25"):
    """插入球员赛季数据"""
    logger.info("写入球员赛季数据...")
    with SessionLocal() as db:
        for s in stats:
            player = db.query(Player).filter(Player.nba_id == s["nba_id"]).first()
            if not player:
                continue

            exists = db.query(PlayerData).filter(
                PlayerData.player_id == player.player_id,
                PlayerData.season == season
            ).first()
            if exists:
                continue

            # 计算衍生指标
            pts = s["points_per_game"]
            fg_pct = s["fg_percentage"]
            three_pct = s["three_percentage"]

            # 估算标准差和变异系数
            points_std = round(pts * random.uniform(0.18, 0.28), 1)
            points_cv = round(points_std / max(pts, 1), 3)

            # 估算高级指标
            per = round(15 + (pts - 10) * 0.5 + random.uniform(-2, 2), 1)
            ts_pct = round(fg_pct * 1.1, 3) if fg_pct > 0 else 0
            usage = round(15 + (pts - 8) * 0.8 + random.uniform(-3, 3), 1)

            # 估算打法分布
            iso_pct = round(random.uniform(0.05, 0.25), 3)
            pr_pct = round(random.uniform(0.10, 0.35), 3)
            spot_pct = round(random.uniform(0.10, 0.30), 3)
            post_pct = round(random.uniform(0.02, 0.15), 3)

            pd = PlayerData(
                player_id=player.player_id,
                season=season,
                team_id=player.team_id,
                games_played=s["games_played"],
                games_started=s["games_started"],
                minutes_per_game=s["minutes_per_game"],
                points_per_game=pts,
                rebounds_per_game=s["rebounds_per_game"],
                assists_per_game=s["assists_per_game"],
                steals_per_game=s["steals_per_game"],
                blocks_per_game=s["blocks_per_game"],
                turnovers_per_game=s["turnovers_per_game"],
                fg_made_per_game=s["fg_made_per_game"],
                fg_attempted_per_game=s["fg_attempted_per_game"],
                fg_percentage=fg_pct,
                three_made_per_game=s["three_made_per_game"],
                three_attempted_per_game=s["three_attempted_per_game"],
                three_percentage=three_pct,
                ft_made_per_game=s["ft_made_per_game"],
                ft_attempted_per_game=s["ft_attempted_per_game"],
                ft_percentage=s["ft_percentage"],
                per=per,
                true_shooting_pct=ts_pct,
                usage_rate=usage,
                isolation_pct=iso_pct,
                pick_roll_pct=pr_pct,
                spot_up_pct=spot_pct,
                post_up_pct=post_pct,
                points_std=points_std,
                points_cv=points_cv,
            )
            db.add(pd)
        db.commit()
    logger.info("球员赛季数据写入完成")


def insert_team_stats(stats: list, season: str = "2024-25"):
    """插入球队赛季数据"""
    logger.info("写入球队赛季数据...")
    with SessionLocal() as db:
        for s in stats:
            exists = db.query(TeamData).filter(
                TeamData.team_id == s["team_id"],
                TeamData.season == season
            ).first()
            if exists:
                continue

            pace = round(random.uniform(96, 104), 1)
            off_rtg = round(s["points_per_game"] / pace * 100, 1)
            def_rtg = round(s["opponent_points"] / pace * 100, 1)

            points_std = round(s["points_per_game"] * random.uniform(0.10, 0.15), 1)
            points_cv = round(points_std / max(s["points_per_game"], 1), 3)

            td = TeamData(
                team_id=s["team_id"],
                season=season,
                wins=s["wins"],
                losses=s["losses"],
                win_percentage=s["win_percentage"],
                points_per_game=s["points_per_game"],
                assists_per_game=s["assists_per_game"],
                rebounds_per_game=s["rebounds_per_game"],
                turnovers_per_game=s["turnovers_per_game"],
                fg_percentage=s["fg_percentage"],
                three_percentage=s["three_percentage"],
                ft_percentage=s["ft_percentage"],
                steals_per_game=s["steals_per_game"],
                blocks_per_game=s["blocks_per_game"],
                opponent_points=s["opponent_points"],
                pace=pace,
                offensive_rating=off_rtg,
                defensive_rating=def_rtg,
                points_std=points_std,
                points_cv=points_cv,
                # 主客场胜率估算
                home_wins=round(s["wins"] * 0.58),
                home_losses=round(s["losses"] * 0.42),
                away_wins=round(s["wins"] * 0.42),
                away_losses=round(s["losses"] * 0.58),
            )
            db.add(td)
        db.commit()

        # 更新球队主客场胜率
        teams = db.query(Team).all()
        for t in teams:
            td = db.query(TeamData).filter(
                TeamData.team_id == t.team_id,
                TeamData.season == season
            ).first()
            if td:
                home_total = (td.home_wins or 0) + (td.home_losses or 0)
                away_total = (td.away_wins or 0) + (td.away_losses or 0)
                if home_total > 0:
                    t.home_win_rate = round(td.home_wins / home_total, 3)
                if away_total > 0:
                    t.away_win_rate = round(td.away_wins / away_total, 3)
        db.commit()
    logger.info("球队赛季数据写入完成")


def insert_sample_games(season: str = "2024-25", count: int = 100):
    """插入示例比赛记录"""
    logger.info("写入示例比赛记录...")
    team_ids = list(TEAM_MAP.values())
    with SessionLocal() as db:
        existing = db.query(GameRecord).filter(GameRecord.season == season).count()
        if existing > 0:
            logger.info(f"已有 {existing} 条比赛记录，跳过")
            return

        base_date = date(2024, 10, 22)
        for i in range(count):
            home_id, away_id = random.sample(team_ids, 2)
            home_score = random.randint(95, 130)
            away_score = random.randint(95, 130)
            if home_score == away_score:
                home_score += 1

            gr = GameRecord(
                nba_game_id=f"00224{i:06d}",
                season=season,
                game_date=base_date + timedelta(days=random.randint(0, 180)),
                game_type="Regular Season",
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=home_score,
                away_score=away_score,
                home_win=1 if home_score > away_score else 0,
                score_diff=home_score - away_score,
                total_score=home_score + away_score,
                is_playoff=0,
                status="FINISHED",
            )
            db.add(gr)
        db.commit()
    logger.info(f"写入 {count} 条比赛记录完成")


def run():
    """执行数据导入"""
    logger.info("=" * 50)
    logger.info("NBA数据导入开始")
    logger.info("=" * 50)

    # 尝试从API获取数据
    players = fetch_players()
    player_stats = fetch_player_stats()
    team_stats = fetch_team_stats()

    if players and player_stats:
        logger.info("使用API数据")
        insert_players(players)
        insert_player_stats(player_stats)
    else:
        logger.warning("API数据获取失败，跳过球员数据导入")

    if team_stats:
        insert_team_stats(team_stats)
    else:
        logger.warning("API数据获取失败，跳过球队数据导入")

    # 插入示例比赛记录
    insert_sample_games()

    logger.info("=" * 50)
    logger.info("数据导入完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
