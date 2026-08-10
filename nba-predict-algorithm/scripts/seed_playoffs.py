"""
2025-26赛季季后赛数据生成
"""
import sys
import random
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, Team, TeamData, GameRecord, BattleRecord, SeriesStar

SEASON = "2025-26"

# 季后赛对阵 (2025-26赛季模拟)
# DB team_id: 25=OKC, 17=DEN, 23=MIN, 16=DAL, 29=SAS, 19=HOU, 26=PHX
# DB team_id: 2=BOS, 6=CLE, 10=MIL, 11=NYK, 13=PHI, 12=ORL, 14=TOR
PLAYOFF_MATCHUPS = {
    # 西部首轮
    "W_R1_G1": {"home": 25, "away": 29, "series": "W_R1_1", "round": "首轮"},   # 雷霆 vs 马刺
    "W_R1_G2": {"home": 17, "away": 26, "series": "W_R1_2", "round": "首轮"},   # 掘金 vs 太阳
    "W_R1_G3": {"home": 23, "away": 19, "series": "W_R1_3", "round": "首轮"},   # 森林狼 vs 火箭
    "W_R1_G4": {"home": 16, "away": 27, "series": "W_R1_4", "round": "首轮"},   # 独行侠 vs 开拓者
    # 东部首轮
    "E_R1_G1": {"home": 2,  "away": 14, "series": "E_R1_1", "round": "首轮"},   # 凯尔特人 vs 猛龙
    "E_R1_G2": {"home": 6,  "away": 13, "series": "E_R1_2", "round": "首轮"},   # 骑士 vs 76人
    "E_R1_G3": {"home": 10, "away": 12, "series": "E_R1_3", "round": "首轮"},   # 雄鹿 vs 魔术
    "E_R1_G4": {"home": 11, "away": 5,  "series": "E_R1_4", "round": "首轮"},   # 尼克斯 vs 公牛
    # 西部半决赛
    "W_R2_G1": {"home": 25, "away": 17, "series": "W_R2_1", "round": "半决赛"},  # 雷霆 vs 掘金
    "W_R2_G2": {"home": 23, "away": 16, "series": "W_R2_2", "round": "半决赛"},  # 森林狼 vs 独行侠
    # 东部半决赛
    "E_R2_G1": {"home": 2,  "away": 10, "series": "E_R2_1", "round": "半决赛"},  # 凯尔特人 vs 雄鹿
    "E_R2_G2": {"home": 6,  "away": 11, "series": "E_R2_2", "round": "半决赛"},  # 骑士 vs 尼克斯
    # 西部决赛
    "W_CF_G1": {"home": 25, "away": 23, "series": "W_CF_1", "round": "决赛"},   # 雷霆 vs 森林狼
    # 东部决赛
    "E_CF_G1": {"home": 2,  "away": 6,  "series": "E_CF_1", "round": "决赛"},   # 凯尔特人 vs 骑士
    # 总决赛
    "F_G1":    {"home": 25, "away": 2,  "series": "F_1",    "round": "总决赛"},  # 雷霆 vs 凯尔特人
}

# 各系列赛结果 (home_wins, away_wins)
SERIES_RESULTS = {
    "W_R1_1": (4, 1), "W_R1_2": (4, 2), "W_R1_3": (4, 3), "W_R1_4": (4, 2),
    "E_R1_1": (4, 0), "E_R1_2": (4, 1), "E_R1_3": (4, 3), "E_R1_4": (4, 2),
    "W_R2_1": (4, 2), "W_R2_2": (4, 3),
    "E_R2_1": (4, 3), "E_R2_2": (4, 1),
    "W_CF_1": (4, 2),
    "E_CF_1": (4, 3),
    "F_1":    (4, 3),
}

# 季后赛球员数据增强 (球员nba_id -> 季后赛场均提升)
# nba_id from seed_data.py, matches DB player.nba_id
# BOS=2: Tatum(1), Brown(2), Porzingis(3)
# CLE=6: Garland(6), Mitchell(7), Mobley(8)
# MIL=10: Giannis(10), Lillard(11)
# NYK=11: Brunson(22)
# OKC=21: SGA(14), JWill(15), Chet(16)
# DEN=17: Jokic(18), Murray(19)
# MIN=18: Edwards(38), KAT(39)
# DAL=7: Luka(26), Kyrie(27)
# MEM=15: Ja Morant(60)
# ORL=12: Banchero(57)
# PHI=13: Embiid(42), Maxey(43)
PLAYOFF_BOOST = {
    "1":   {"pts": 28.5, "fg": 0.48, "reb": 8.5, "ast": 5.5},   # Tatum (BOS)
    "2":   {"pts": 24.0, "fg": 0.50, "reb": 5.5, "ast": 3.5},   # Brown (BOS)
    "3":   {"pts": 18.0, "fg": 0.52, "reb": 7.0, "ast": 2.0},   # Porzingis (BOS)
    "6":   {"pts": 24.5, "fg": 0.47, "reb": 3.5, "ast": 8.0},   # Garland (CLE)
    "7":   {"pts": 30.0, "fg": 0.46, "reb": 5.0, "ast": 5.5},   # Mitchell (CLE)
    "8":   {"pts": 18.5, "fg": 0.55, "reb": 9.5, "ast": 3.0},   # Mobley (CLE)
    "10":  {"pts": 32.0, "fg": 0.55, "reb": 12.0, "ast": 6.0},  # Giannis (MIL)
    "11":  {"pts": 26.0, "fg": 0.44, "reb": 4.0, "ast": 7.0},   # Lillard (MIL)
    "14":  {"pts": 33.5, "fg": 0.52, "reb": 5.5, "ast": 6.2},   # SGA (OKC)
    "15":  {"pts": 21.0, "fg": 0.48, "reb": 6.0, "ast": 5.0},   # Jalen Williams (OKC)
    "16":  {"pts": 16.5, "fg": 0.55, "reb": 9.0, "ast": 2.0},   # Chet Holmgren (OKC)
    "18":  {"pts": 28.0, "fg": 0.56, "reb": 13.0, "ast": 10.0}, # Jokic (DEN)
    "19":  {"pts": 23.0, "fg": 0.47, "reb": 4.5, "ast": 6.5},   # Murray (DEN)
    "22":  {"pts": 29.0, "fg": 0.47, "reb": 3.5, "ast": 7.0},   # Brunson (NYK)
    "26":  {"pts": 32.0, "fg": 0.48, "reb": 9.0, "ast": 8.5},   # Luka (DAL)
    "27":  {"pts": 25.0, "fg": 0.49, "reb": 4.0, "ast": 5.0},   # Kyrie (DAL)
    "38":  {"pts": 28.5, "fg": 0.47, "reb": 5.5, "ast": 5.0},   # Edwards (MIN)
    "39":  {"pts": 21.0, "fg": 0.52, "reb": 9.0, "ast": 3.0},   # KAT (MIN)
    "42":  {"pts": 25.0, "fg": 0.48, "reb": 10.5, "ast": 3.5},  # Embiid (PHI)
    "43":  {"pts": 26.0, "fg": 0.46, "reb": 4.0, "ast": 6.0},   # Maxey (PHI)
    "57":  {"pts": 26.5, "fg": 0.49, "reb": 8.0, "ast": 5.0},   # Banchero (ORL)
    "60":  {"pts": 27.0, "fg": 0.46, "reb": 5.0, "ast": 8.5},   # Ja Morant (MEM)
}

# 系列赛ID映射
SERIES_ID_MAP = {
    "W_R1_1": 1, "W_R1_2": 2, "W_R1_3": 3, "W_R1_4": 4,
    "E_R1_1": 5, "E_R1_2": 6, "E_R1_3": 7, "E_R1_4": 8,
    "W_R2_1": 9, "W_R2_2": 10, "E_R2_1": 11, "E_R2_2": 12,
    "W_CF_1": 13, "E_CF_1": 14, "F_1": 15,
}


def seed_202526_team_data():
    """写入2025-26赛季球队数据"""
    logger.info("写入2025-26赛季球队数据...")
    with SessionLocal() as db:
        existing = db.query(TeamData).filter(TeamData.season == SEASON).count()
        if existing > 0:
            logger.info(f"已有 {existing} 条2025-26球队数据，跳过")
            return

        teams = db.query(Team).all()
        for team in teams:
            # 基于上赛季数据微调
            prev = db.query(TeamData).filter(
                TeamData.team_id == team.team_id,
                TeamData.season == "2024-25"
            ).first()

            if prev:
                wins = min(82, max(10, prev.wins + random.randint(-5, 8)))
                losses = 82 - wins
                pts = round(prev.points_per_game + random.uniform(-2, 3), 1)
                opp_pts = round(prev.opponent_points + random.uniform(-2, 2), 1)
                td = TeamData(
                    team_id=team.team_id,
                    season=SEASON,
                    wins=wins, losses=losses,
                    win_percentage=round(wins / 82, 3),
                    home_wins=round(wins * 0.60), home_losses=round(losses * 0.40),
                    away_wins=round(wins * 0.40), away_losses=round(losses * 0.60),
                    points_per_game=pts,
                    assists_per_game=round(prev.assists_per_game + random.uniform(-1, 1), 1),
                    rebounds_per_game=round(prev.rebounds_per_game + random.uniform(-1, 1), 1),
                    turnovers_per_game=prev.turnovers_per_game,
                    fg_percentage=round(prev.fg_percentage + random.uniform(-0.02, 0.02), 3),
                    three_percentage=round(prev.three_percentage + random.uniform(-0.02, 0.02), 3),
                    ft_percentage=prev.ft_percentage,
                    steals_per_game=prev.steals_per_game,
                    blocks_per_game=prev.blocks_per_game,
                    opponent_points=opp_pts,
                    opponent_fg_percentage=prev.opponent_fg_percentage,
                    opponent_three_pct=prev.opponent_three_pct,
                    pace=prev.pace,
                    offensive_rating=round(pts / prev.pace * 100, 1),
                    defensive_rating=round(opp_pts / prev.pace * 100, 1),
                    points_std=round(pts * 0.12, 1),
                    points_cv=round(0.12, 3),
                    fast_break_points=prev.fast_break_points,
                    points_in_paint=prev.points_in_paint,
                    second_chance_points=prev.second_chance_points,
                    bench_points=prev.bench_points,
                )
                db.add(td)
        db.commit()
    logger.info("2025-26赛季球队数据写入完成")


def seed_202526_player_data():
    """写入2025-26赛季球员数据"""
    logger.info("写入2025-26赛季球员数据...")
    with SessionLocal() as db:
        existing = db.query(PlayerData).filter(PlayerData.season == SEASON).count()
        if existing > 0:
            logger.info(f"已有 {existing} 条2025-26球员数据，跳过")
            return

        players = db.query(Player).filter(Player.status == 1).all()
        for p in players:
            prev = db.query(PlayerData).filter(
                PlayerData.player_id == p.player_id,
                PlayerData.season == "2024-25"
            ).first()
            if not prev:
                continue

            # 年龄增长
            if p.age:
                p.age = p.age + 1

            pts = round(prev.points_per_game + random.uniform(-2, 3), 1)
            fg = round(min(0.65, max(0.35, prev.fg_percentage + random.uniform(-0.03, 0.03))), 3)

            pd = PlayerData(
                player_id=p.player_id,
                season=SEASON,
                team_id=p.team_id,
                games_played=max(1, prev.games_played + random.randint(-5, 5)),
                games_started=prev.games_started,
                minutes_per_game=prev.minutes_per_game,
                points_per_game=pts,
                rebounds_per_game=round(prev.rebounds_per_game + random.uniform(-0.5, 0.5), 1),
                assists_per_game=round(prev.assists_per_game + random.uniform(-0.5, 0.5), 1),
                steals_per_game=prev.steals_per_game,
                blocks_per_game=prev.blocks_per_game,
                turnovers_per_game=prev.turnovers_per_game,
                fg_made_per_game=round(prev.fg_made_per_game + random.uniform(-0.3, 0.3), 1),
                fg_attempted_per_game=round(prev.fg_attempted_per_game + random.uniform(-0.5, 0.5), 1),
                fg_percentage=fg,
                three_made_per_game=prev.three_made_per_game,
                three_attempted_per_game=prev.three_attempted_per_game,
                three_percentage=round(min(0.50, max(0.20, prev.three_percentage + random.uniform(-0.02, 0.02))), 3),
                ft_made_per_game=prev.ft_made_per_game,
                ft_attempted_per_game=prev.ft_attempted_per_game,
                ft_percentage=prev.ft_percentage,
                per=round(prev.per + random.uniform(-1, 2), 1),
                true_shooting_pct=round(fg * 1.05, 3),
                usage_rate=round(prev.usage_rate + random.uniform(-2, 2), 1),
                isolation_pct=prev.isolation_pct,
                pick_roll_pct=prev.pick_roll_pct,
                spot_up_pct=prev.spot_up_pct,
                post_up_pct=prev.post_up_pct,
                points_std=round(pts * random.uniform(0.18, 0.25), 1),
                points_cv=round(random.uniform(0.18, 0.25), 3),
            )
            db.add(pd)
        db.commit()
    logger.info(f"2025-26赛季球员数据写入完成")


def seed_playoff_games():
    """写入季后赛比赛记录"""
    logger.info("写入季后赛比赛记录...")
    with SessionLocal() as db:
        existing = db.query(GameRecord).filter(
            GameRecord.season == SEASON,
            GameRecord.is_playoff == 1
        ).count()
        if existing > 0:
            logger.info(f"已有 {existing} 条季后赛记录，跳过")
            return

        base_date = date(2026, 4, 19)
        game_count = 0

        for key, matchup in PLAYOFF_MATCHUPS.items():
            home_id = matchup["home"]
            away_id = matchup["away"]
            series_id = matchup["series"]
            result = SERIES_RESULTS.get(series_id, (4, 2))
            total_games = result[0] + result[1]

            for game_num in range(1, total_games + 1):
                # 主客场交替
                if game_num <= 2:
                    h, a = home_id, away_id
                elif game_num <= 5:
                    h, a = (away_id, home_id) if game_num % 2 == 1 else (home_id, away_id)
                else:
                    h, a = home_id, away_id

                # 根据系列赛结果决定胜负
                if game_num <= result[0]:
                    home_win = 1 if h == home_id else 0
                else:
                    home_win = 0 if h == home_id else 1

                home_base = random.randint(105, 125)
                away_base = random.randint(100, 120)
                if home_win:
                    home_score = max(home_base, away_base + random.randint(1, 12))
                    away_score = min(away_base, home_score - random.randint(1, 12))
                else:
                    away_score = max(away_base, home_base + random.randint(1, 12))
                    home_score = min(home_base, away_score - random.randint(1, 12))

                gr = GameRecord(
                    nba_game_id=f"00425{game_count:06d}",
                    season=SEASON,
                    game_date=base_date + timedelta(days=game_count * 2),
                    game_type="Playoffs",
                    home_team_id=h,
                    away_team_id=a,
                    home_score=home_score,
                    away_score=away_score,
                    home_win=1 if home_score > away_score else 0,
                    score_diff=home_score - away_score,
                    total_score=home_score + away_score,
                    is_playoff=1,
                    status="FINISHED",
                )
                db.add(gr)
                game_count += 1

        db.commit()
    logger.info(f"写入 {game_count} 条季后赛记录完成")


def seed_battle_records():
    """写入交锋记录"""
    logger.info("写入季后赛交锋记录...")
    with SessionLocal() as db:
        for series_id, (home_w, away_w) in SERIES_RESULTS.items():
            # 找到对应的对阵
            matchup = None
            for v in PLAYOFF_MATCHUPS.values():
                if v["series"] == series_id:
                    matchup = v
                    break
            if not matchup:
                continue

            t1, t2 = matchup["home"], matchup["away"]
            existing = db.query(BattleRecord).filter(
                BattleRecord.team1_id == t1,
                BattleRecord.team2_id == t2,
                BattleRecord.season == SEASON
            ).first()
            if existing:
                continue

            br = BattleRecord(
                team1_id=t1, team2_id=t2, season=SEASON,
                total_games=home_w + away_w,
                team1_wins=home_w, team2_wins=away_w,
                team1_avg_score=round(random.uniform(108, 118), 1),
                team2_avg_score=round(random.uniform(105, 115), 1),
                avg_score_diff=round(home_w - away_w + random.uniform(-2, 2), 1),
            )
            db.add(br)
        db.commit()
    logger.info("交锋记录写入完成")


def seed_series_stars():
    """写入季后赛之星"""
    logger.info("写入季后赛之星...")
    with SessionLocal() as db:
        existing = db.query(SeriesStar).filter(SeriesStar.season == SEASON).count()
        if existing > 0:
            logger.info(f"已有 {existing} 条季后赛之星，跳过")
            return

        for nba_id_str, stats in PLAYOFF_BOOST.items():
            player = db.query(Player).filter(Player.nba_id == nba_id_str).first()
            if not player:
                continue

            prev = db.query(PlayerData).filter(
                PlayerData.player_id == player.player_id,
                PlayerData.season == SEASON
            ).first()
            base_pts = prev.points_per_game if prev else 15.0
            base_fg = prev.fg_percentage if prev else 0.45

            score_up = round(stats["pts"] - base_pts, 1)
            hit_rate_up = round(stats["fg"] - base_fg, 3)

            # 找到对手球队和系列赛ID
            opponent_id = 0
            series_id = 1
            for key, v in PLAYOFF_MATCHUPS.items():
                if v["home"] == player.team_id:
                    opponent_id = v["away"]
                    series_id = SERIES_ID_MAP.get(v["series"], 1)
                    break
                elif v["away"] == player.team_id:
                    opponent_id = v["home"]
                    series_id = SERIES_ID_MAP.get(v["series"], 1)
                    break
            if opponent_id == 0:
                continue  # 球队不在季后赛中，跳过

            ss = SeriesStar(
                series_id=series_id,
                player_id=player.player_id,
                team_id=player.team_id,
                opponent_team_id=opponent_id,
                season=SEASON,
                avg_score=stats["pts"],
                avg_fg_pct=stats["fg"],
                score_up=score_up,
                hit_rate_up=hit_rate_up,
                judge_threshold_score=5.0,
                judge_threshold_pct=0.10,
                is_star=1 if score_up >= 5.0 else 0,
                key_game_score=round(stats["pts"] * 1.15),
                key_game_fg_pct=round(stats["fg"] * 1.05, 3),
            )
            db.add(ss)
        db.commit()
    logger.info("季后赛之星写入完成")


def run():
    logger.info("=" * 50)
    logger.info("2025-26季后赛数据生成开始")
    logger.info("=" * 50)

    seed_202526_team_data()
    seed_202526_player_data()
    seed_playoff_games()
    seed_battle_records()
    seed_series_stars()

    logger.info("=" * 50)
    logger.info("季后赛数据生成完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
