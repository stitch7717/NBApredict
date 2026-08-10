"""
NBA种子数据生成脚本
生成2024-25赛季球员和球队数据用于测试
"""
import sys
import random
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy import text
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, Team, TeamData, GameRecord

SEASON = "2024-25"

# NBA球队数据 (abbreviation -> (进攻型/防守型, 实力等级1-5))
# 使用abbreviation作为key，运行时从DB查找正确的team_id
TEAM_PROFILES = {
    "ATL": (3, 3),   # 老鹰
    "BOS": (4, 5),   # 凯尔特人
    "BKN": (2, 2),   # 篮网
    "CHA": (2, 2),   # 黄蜂
    "CHI": (3, 3),   # 公牛
    "CLE": (4, 5),   # 骑士
    "DAL": (5, 4),   # 独行侠
    "DEN": (4, 4),   # 掘金
    "DET": (2, 2),   # 活塞
    "GSW": (5, 4),   # 勇士
    "HOU": (3, 4),   # 火箭
    "IND": (4, 3),   # 步行者
    "LAC": (3, 3),   # 快船
    "LAL": (4, 4),   # 湖人
    "MEM": (3, 4),   # 灰熊
    "MIA": (3, 4),   # 热火
    "MIL": (4, 5),   # 雄鹿
    "MIN": (3, 4),   # 森林狼
    "NOP": (3, 3),   # 鹈鹕
    "NYK": (4, 4),   # 尼克斯
    "OKC": (4, 5),   # 雷霆
    "ORL": (3, 4),   # 魔术
    "PHI": (4, 4),   # 76人
    "PHX": (4, 3),   # 太阳
    "POR": (3, 2),   # 开拓者
    "SAC": (4, 3),   # 国王
    "SAS": (3, 2),   # 马刺
    "TOR": (3, 2),   # 猛龙
    "UTA": (3, 2),   # 爵士
    "WAS": (2, 1),   # 奇才
}


def _get_team_id_map():
    """从数据库获取 abbreviation -> team_id 映射"""
    with SessionLocal() as db:
        teams = db.query(Team).all()
        return {t.abbreviation: t.team_id for t in teams}


# 核心球员数据 (nba_id, name, team_abbr, position, age, all_star, injury, player_type)
# 使用abbreviation，运行时转换为DB team_id

# 核心球员数据 (nba_id, name, team_abbr, position, age, all_star, injury, player_type)
PLAYERS = [
    ("1628369", "Jayson Tatum", "BOS", "SF", 27, 6, "HEALTHY", "全能型"),
    ("1627759", "Jaylen Brown", "BOS", "SG", 28, 3, "HEALTHY", "得分型"),
    ("203901", "Kristaps Porzingis", "BOS", "C", 29, 1, "HEALTHY", "内线型"),
    ("1628401", "Derrick White", "BOS", "PG", 31, 0, "HEALTHY", "3D型"),
    ("202699", "Jrue Holiday", "BOS", "PG", 34, 0, "HEALTHY", "3D型"),
    ("1630173", "Darius Garland", "CLE", "PG", 25, 2, "HEALTHY", "组织型"),
    ("1628381", "Donovan Mitchell", "CLE", "SG", 28, 5, "HEALTHY", "得分型"),
    ("1629631", "Evan Mobley", "CLE", "PF", 24, 1, "HEALTHY", "全能型"),
    ("202689", "Jarrett Allen", "CLE", "C", 27, 1, "HEALTHY", "内线型"),
    ("203507", "Giannis Antetokounmpo", "MIL", "PF", 30, 8, "HEALTHY", "全能型"),
    ("203081", "Damian Lillard", "MIL", "PG", 34, 8, "HEALTHY", "得分型"),
    ("201572", "Khris Middleton", "MIL", "SF", 34, 3, "RECOVERY", "得分型"),
    ("1627752", "Brook Lopez", "MIL", "C", 37, 1, "HEALTHY", "内线型"),
    ("1630178", "Shai Gilgeous-Alexander", "OKC", "SG", 26, 3, "HEALTHY", "得分型"),
    ("1631094", "Jalen Williams", "OKC", "SF", 24, 1, "HEALTHY", "全能型"),
    ("1631114", "Chet Holmgren", "OKC", "C", 23, 0, "HEALTHY", "内线型"),
    ("1629640", "Lu Dort", "OKC", "SG", 26, 0, "HEALTHY", "防守型"),
    ("203999", "Nikola Jokic", "DEN", "C", 30, 7, "HEALTHY", "全能型"),
    ("1627750", "Jamal Murray", "DEN", "PG", 28, 0, "HEALTHY", "得分型"),
    ("1629004", "Michael Porter Jr.", "DEN", "SF", 26, 0, "HEALTHY", "投射型"),
    ("1628510", "Aaron Gordon", "DEN", "PF", 30, 0, "HEALTHY", "3D型"),
    ("1628384", "Jalen Brunson", "NYK", "PG", 28, 2, "HEALTHY", "组织型"),
    ("1630581", "OG Anunoby", "NYK", "SF", 27, 0, "HEALTHY", "3D型"),
    ("203944", "Julius Randle", "NYK", "PF", 30, 3, "HEALTHY", "全能型"),
    ("1629630", "Donte DiVincenzo", "NYK", "SG", 28, 0, "HEALTHY", "3D型"),
    ("2544", "LeBron James", "LAL", "SF", 40, 20, "HEALTHY", "全能型"),
    ("203076", "Anthony Davis", "LAL", "PF", 32, 9, "HEALTHY", "内线型"),
    ("1630268", "Austin Reaves", "LAL", "SG", 26, 0, "HEALTHY", "组织型"),
    ("1626156", "D'Angelo Russell", "LAL", "PG", 29, 1, "HEALTHY", "组织型"),
    ("1629029", "Luka Doncic", "DAL", "PG", 26, 5, "HEALTHY", "全能型"),
    ("202681", "Kyrie Irving", "DAL", "SG", 33, 8, "HEALTHY", "得分型"),
    ("1628464", "PJ Washington", "DAL", "PF", 27, 0, "HEALTHY", "3D型"),
    ("1627827", "Daniel Gafford", "DAL", "C", 26, 0, "HEALTHY", "内线型"),
    ("201939", "Stephen Curry", "GSW", "PG", 37, 10, "HEALTHY", "得分型"),
    ("203110", "Draymond Green", "GSW", "PF", 35, 4, "HEALTHY", "防守型"),
    ("1626172", "Andrew Wiggins", "GSW", "SF", 30, 1, "HEALTHY", "3D型"),
    ("1630228", "Jonathan Kuminga", "GSW", "SF", 22, 0, "HEALTHY", "全能型"),
    ("1630162", "Anthony Edwards", "MIN", "SG", 24, 2, "HEALTHY", "得分型"),
    ("1626157", "Karl-Anthony Towns", "MIN", "C", 29, 4, "HEALTHY", "内线型"),
    ("203497", "Rudy Gobert", "MIN", "C", 32, 3, "HEALTHY", "防守型"),
    ("1631095", "Jaden McDaniels", "MIN", "SF", 24, 0, "HEALTHY", "防守型"),
    ("203954", "Joel Embiid", "PHI", "C", 31, 7, "RECOVERY", "内线型"),
    ("1630209", "Tyrese Maxey", "PHI", "PG", 24, 1, "HEALTHY", "得分型"),
    ("202331", "Paul George", "PHI", "SF", 35, 9, "HEALTHY", "全能型"),
    ("202710", "Jimmy Butler", "MIA", "SF", 35, 6, "HEALTHY", "全能型"),
    ("1628389", "Bam Adebayo", "MIA", "C", 28, 3, "HEALTHY", "内线型"),
    ("1629639", "Tyler Herro", "MIA", "SG", 25, 0, "HEALTHY", "得分型"),
    ("1628368", "De'Aaron Fox", "SAC", "PG", 27, 1, "HEALTHY", "得分型"),
    ("202087", "Domantas Sabonis", "SAC", "C", 28, 3, "HEALTHY", "全能型"),
    ("201942", "DeMar DeRozan", "SAC", "SF", 36, 6, "HEALTHY", "得分型"),
    ("201142", "Kevin Durant", "PHX", "SF", 36, 14, "HEALTHY", "得分型"),
    ("1626164", "Devin Booker", "PHX", "SG", 28, 4, "HEALTHY", "得分型"),
    ("203078", "Bradley Beal", "PHX", "SG", 32, 3, "HEALTHY", "得分型"),
    ("1630178", "Jalen Green", "HOU", "SG", 23, 0, "HEALTHY", "得分型"),
    ("1631110", "Alperen Sengun", "HOU", "C", 22, 0, "HEALTHY", "内线型"),
    ("1641713", "Amen Thompson", "HOU", "SF", 22, 0, "HEALTHY", "全能型"),
    ("1631094", "Paolo Banchero", "ORL", "PF", 22, 1, "HEALTHY", "全能型"),
    ("1630532", "Franz Wagner", "ORL", "SF", 23, 0, "HEALTHY", "全能型"),
    ("1630591", "Jalen Suggs", "ORL", "PG", 23, 0, "HEALTHY", "防守型"),
    ("1629630", "Ja Morant", "MEM", "PG", 25, 2, "HEALTHY", "得分型"),
    ("1630216", "Desmond Bane", "MEM", "SG", 26, 0, "HEALTHY", "3D型"),
    ("1629633", "Jaren Jackson Jr.", "MEM", "PF", 25, 1, "HEALTHY", "防守型"),
    ("1630169", "Tyrese Haliburton", "IND", "PG", 25, 2, "HEALTHY", "组织型"),
    ("1627783", "Pascal Siakam", "IND", "PF", 31, 2, "HEALTHY", "全能型"),
    ("1626167", "Myles Turner", "IND", "C", 28, 0, "HEALTHY", "防守型"),
    ("1629027", "Trae Young", "ATL", "PG", 26, 4, "HEALTHY", "组织型"),
    ("1627750", "Dejounte Murray", "ATL", "SG", 28, 1, "HEALTHY", "全能型"),
    ("1627750", "Zach LaVine", "CHI", "SG", 30, 2, "HEALTHY", "得分型"),
    ("202696", "Nikola Vucevic", "CHI", "C", 34, 2, "HEALTHY", "内线型"),
    ("1629627", "Zion Williamson", "NOP", "PF", 24, 2, "HEALTHY", "内线型"),
    ("1627742", "Brandon Ingram", "NOP", "SF", 27, 1, "HEALTHY", "得分型"),
    ("1630168", "Anfernee Simons", "POR", "SG", 25, 0, "HEALTHY", "得分型"),
    ("203924", "Jerami Grant", "POR", "PF", 31, 0, "HEALTHY", "全能型"),
    ("1641706", "Victor Wembanyama", "SAS", "C", 21, 1, "HEALTHY", "全能型"),
    ("1630170", "Devin Vassell", "SAS", "SG", 24, 0, "HEALTHY", "3D型"),
    ("1630173", "LaMelo Ball", "CHA", "PG", 23, 1, "HEALTHY", "组织型"),
    ("202087", "Miles Bridges", "CHA", "PF", 26, 0, "HEALTHY", "全能型"),
    ("1630595", "Cade Cunningham", "DET", "PG", 23, 0, "HEALTHY", "全能型"),
    ("1630598", "Jaden Ivey", "DET", "SG", 22, 0, "HEALTHY", "得分型"),
    ("1630578", "Scottie Barnes", "TOR", "SF", 23, 1, "HEALTHY", "全能型"),
    ("1629628", "RJ Barrett", "TOR", "SF", 24, 0, "HEALTHY", "得分型"),
    ("1629028", "Lauri Markkanen", "UTA", "PF", 27, 1, "HEALTHY", "投射型"),
    ("1629012", "Collin Sexton", "UTA", "SG", 26, 0, "HEALTHY", "得分型"),
    ("1628398", "Kyle Kuzma", "WAS", "PF", 29, 0, "HEALTHY", "全能型"),
    ("1629673", "Jordan Poole", "WAS", "SG", 25, 0, "HEALTHY", "得分型"),
    ("1629629", "Cameron Johnson", "BKN", "SF", 28, 0, "HEALTHY", "3D型"),
    ("1630206", "Mikal Bridges", "BKN", "SF", 28, 0, "HEALTHY", "3D型"),
    ("202695", "Kawhi Leonard", "LAC", "SF", 33, 5, "INJURED", "全能型"),
    ("202331", "James Harden", "LAC", "PG", 35, 10, "HEALTHY", "组织型"),
]


def generate_player_stats(player_type: str, age: int, all_star: int, injury: str):
    """根据球员类型生成合理的赛季数据"""
    # 基础数据模板
    templates = {
        "得分型":    {"pts": (22, 8), "reb": (4, 2), "ast": (4, 2), "fg": (0.46, 0.05), "three": (0.37, 0.04), "usage": (28, 5)},
        "组织型":    {"pts": (18, 6), "reb": (4, 2), "ast": (9, 3), "fg": (0.45, 0.05), "three": (0.35, 0.04), "usage": (25, 4)},
        "3D型":     {"pts": (12, 4), "reb": (5, 2), "ast": (2, 1), "fg": (0.44, 0.04), "three": (0.39, 0.04), "usage": (16, 3)},
        "内线型":    {"pts": (16, 6), "reb": (10, 3), "ast": (2, 1), "fg": (0.55, 0.05), "three": (0.25, 0.08), "usage": (22, 4)},
        "全能型":    {"pts": (20, 8), "reb": (7, 3), "ast": (5, 2), "fg": (0.48, 0.05), "three": (0.35, 0.04), "usage": (26, 5)},
        "防守型":    {"pts": (8, 3), "reb": (6, 2), "ast": (2, 1), "fg": (0.48, 0.04), "three": (0.33, 0.05), "usage": (14, 3)},
        "投射型":    {"pts": (14, 5), "reb": (4, 2), "ast": (2, 1), "fg": (0.44, 0.04), "three": (0.40, 0.04), "usage": (18, 4)},
    }

    t = templates.get(player_type, templates["得分型"])

    # 全明星加成
    star_boost = min(all_star * 0.5, 5)

    # 年龄因素
    age_factor = 1.0
    if age > 35:
        age_factor = 0.90
    elif age > 33:
        age_factor = 0.95

    # 伤病因素
    injury_factor = 1.0
    if injury == "INJURED":
        injury_factor = 0.0
    elif injury == "RECOVERY":
        injury_factor = 0.7

    gp = max(1, int(random.uniform(55, 82) * injury_factor))
    gs = max(0, int(gp * random.uniform(0.5, 1.0)))
    minutes = round(random.uniform(28, 36) * age_factor, 1)

    pts = round(max(3, random.gauss(t["pts"][0] + star_boost, t["pts"][1]) * age_factor), 1)
    reb = round(max(1, random.gauss(t["reb"][0], t["reb"][1])), 1)
    ast = round(max(0.5, random.gauss(t["ast"][0], t["ast"][1])), 1)
    stl = round(max(0.2, random.gauss(1.0, 0.3)), 1)
    blk = round(max(0.1, random.gauss(0.6, 0.4)), 1)
    tov = round(max(0.5, random.gauss(2.0, 0.6)), 1)

    fg_pct = round(min(0.65, max(0.35, random.gauss(t["fg"][0], t["fg"][1]))), 3)
    three_pct = round(min(0.50, max(0.20, random.gauss(t["three"][0], t["three"][1]))), 3)
    ft_pct = round(min(0.95, max(0.55, random.gauss(0.78, 0.08))), 3)

    fg_att = round(pts / (fg_pct * 2 + three_pct) if fg_pct > 0 else 10, 1)
    fg_made = round(fg_att * fg_pct, 1)
    three_att = round(fg_att * random.uniform(0.25, 0.50), 1)
    three_made = round(three_att * three_pct, 1)
    ft_att = round(random.uniform(2, 8), 1)
    ft_made = round(ft_att * ft_pct, 1)

    usage = round(max(10, random.gauss(t["usage"][0], t["usage"][1])), 1)
    per = round(15 + (pts - 10) * 0.4 + (ast - 3) * 0.2 + (reb - 4) * 0.1 + random.uniform(-2, 2), 1)
    ts_pct = round(fg_pct * 1.05, 3)

    points_std = round(pts * random.uniform(0.18, 0.28), 1)
    points_cv = round(points_std / max(pts, 1), 3)

    iso_pct = round(random.uniform(0.05, 0.25), 3)
    pr_pct = round(random.uniform(0.10, 0.35), 3)
    spot_pct = round(random.uniform(0.10, 0.30), 3)
    post_pct = round(random.uniform(0.02, 0.15), 3)

    return {
        "games_played": gp,
        "games_started": gs,
        "minutes_per_game": minutes,
        "points_per_game": pts,
        "rebounds_per_game": reb,
        "assists_per_game": ast,
        "steals_per_game": stl,
        "blocks_per_game": blk,
        "turnovers_per_game": tov,
        "fg_made_per_game": fg_made,
        "fg_attempted_per_game": fg_att,
        "fg_percentage": fg_pct,
        "three_made_per_game": three_made,
        "three_attempted_per_game": three_att,
        "three_percentage": three_pct,
        "ft_made_per_game": ft_made,
        "ft_attempted_per_game": ft_att,
        "ft_percentage": ft_pct,
        "per": per,
        "true_shooting_pct": ts_pct,
        "usage_rate": usage,
        "isolation_pct": iso_pct,
        "pick_roll_pct": pr_pct,
        "spot_up_pct": spot_pct,
        "post_up_pct": post_pct,
        "points_std": points_std,
        "points_cv": points_cv,
    }


def generate_team_data(abbr: str, style: int, strength: int):
    """根据球队风格和实力生成赛季数据"""
    base_wins = {1: 20, 2: 32, 3: 42, 4: 50, 5: 58}
    wins = base_wins[strength] + random.randint(-5, 5)
    losses = 82 - wins
    win_pct = round(wins / 82, 3)

    # 进攻型球队得分更高，防守型球队失分更低
    if style >= 4:  # 进攻型
        pts = round(random.gauss(115, 3), 1)
        opp_pts = round(random.gauss(112, 3), 1)
    elif style <= 2:  # 防守型
        pts = round(random.gauss(108, 3), 1)
        opp_pts = round(random.gauss(106, 3), 1)
    else:  # 均衡
        pts = round(random.gauss(112, 3), 1)
        opp_pts = round(random.gauss(110, 3), 1)

    pace = round(random.uniform(96, 104), 1)
    off_rtg = round(pts / pace * 100, 1)
    def_rtg = round(opp_pts / pace * 100, 1)

    points_std = round(pts * random.uniform(0.10, 0.15), 1)
    points_cv = round(points_std / max(pts, 1), 3)

    return {
        "wins": wins,
        "losses": losses,
        "win_percentage": win_pct,
        "home_wins": round(wins * random.uniform(0.55, 0.65)),
        "home_losses": round(losses * random.uniform(0.35, 0.45)),
        "away_wins": round(wins * random.uniform(0.35, 0.45)),
        "away_losses": round(losses * random.uniform(0.55, 0.65)),
        "points_per_game": pts,
        "assists_per_game": round(random.gauss(25, 3), 1),
        "rebounds_per_game": round(random.gauss(44, 3), 1),
        "turnovers_per_game": round(random.gauss(14, 2), 1),
        "fg_percentage": round(random.uniform(0.44, 0.50), 3),
        "three_percentage": round(random.uniform(0.34, 0.40), 3),
        "ft_percentage": round(random.uniform(0.75, 0.82), 3),
        "steals_per_game": round(random.gauss(7.5, 1.5), 1),
        "blocks_per_game": round(random.gauss(5.0, 1.5), 1),
        "opponent_points": opp_pts,
        "opponent_fg_percentage": round(random.uniform(0.43, 0.48), 3),
        "opponent_three_pct": round(random.uniform(0.33, 0.38), 3),
        "pace": pace,
        "offensive_rating": off_rtg,
        "defensive_rating": def_rtg,
        "points_std": points_std,
        "points_cv": points_cv,
        "fast_break_points": round(random.gauss(14, 3), 1),
        "points_in_paint": round(random.gauss(48, 5), 1),
        "second_chance_points": round(random.gauss(12, 2), 1),
        "bench_points": round(random.gauss(35, 5), 1),
    }


def seed_players():
    """写入球员数据"""
    logger.info("写入球员数据...")
    team_map = _get_team_id_map()
    with SessionLocal() as db:
        for idx, (nba_id, name, team_abbr, pos, age, all_star, injury, ptype) in enumerate(PLAYERS, 1):
            nba_id = str(idx)
            exists = db.query(Player).filter(Player.nba_id == nba_id).first()
            if exists:
                continue
            team_id = team_map.get(team_abbr)
            if not team_id:
                logger.warning(f"球队 {team_abbr} 不存在，跳过 {name}")
                continue
            player = Player(
                nba_id=nba_id,
                player_name=name,
                player_name_en=name,
                position=pos,
                team_id=team_id,
                age=age,
                all_star_count=all_star,
                injury_status=injury,
                player_type=ptype,
                status=1,
            )
            db.add(player)
        db.commit()
    logger.info(f"写入 {len(PLAYERS)} 名球员完成")


def seed_player_data():
    """写入球员赛季数据"""
    logger.info("写入球员赛季数据...")
    team_map = _get_team_id_map()
    count = 0
    with SessionLocal() as db:
        for idx, (nba_id, name, team_abbr, pos, age, all_star, injury, ptype) in enumerate(PLAYERS, 1):
            nba_id = str(idx)
            player = db.query(Player).filter(Player.nba_id == nba_id).first()
            if not player:
                continue

            exists = db.query(PlayerData).filter(
                PlayerData.player_id == player.player_id,
                PlayerData.season == SEASON
            ).first()
            if exists:
                continue

            team_id = team_map.get(team_abbr, player.team_id)
            stats = generate_player_stats(ptype, age, all_star, injury)
            pd = PlayerData(
                player_id=player.player_id,
                season=SEASON,
                team_id=team_id,
                **stats,
            )
            db.add(pd)
            count += 1
        db.commit()
    logger.info(f"写入 {count} 名球员赛季数据完成")


def seed_team_data():
    """写入球队赛季数据"""
    logger.info("写入球队赛季数据...")
    team_map = _get_team_id_map()
    count = 0
    with SessionLocal() as db:
        for abbr, (style, strength) in TEAM_PROFILES.items():
            team_id = team_map.get(abbr)
            if not team_id:
                continue
            exists = db.query(TeamData).filter(
                TeamData.team_id == team_id,
                TeamData.season == SEASON
            ).first()
            if exists:
                continue

            stats = generate_team_data(abbr, style, strength)
            td = TeamData(team_id=team_id, season=SEASON, **stats)
            db.add(td)

            team = db.query(Team).filter(Team.team_id == team_id).first()
            if team:
                home_total = stats["home_wins"] + stats["home_losses"]
                away_total = stats["away_wins"] + stats["away_losses"]
                if home_total > 0:
                    team.home_win_rate = round(stats["home_wins"] / home_total, 3)
                if away_total > 0:
                    team.away_win_rate = round(stats["away_wins"] / away_total, 3)
            count += 1
        db.commit()
    logger.info(f"写入 {count} 支球队赛季数据完成")


def seed_games(count: int = 200):
    """写入示例比赛记录"""
    logger.info("写入比赛记录...")
    team_map = _get_team_id_map()
    # team_id -> (style, strength) mapping
    id_to_profile = {v: TEAM_PROFILES[k] for k, v in team_map.items() if k in TEAM_PROFILES}
    with SessionLocal() as db:
        existing = db.query(GameRecord).filter(GameRecord.season == SEASON).count()
        if existing >= count:
            logger.info(f"已有 {existing} 条比赛记录，跳过")
            return

        team_ids = list(team_map.values())
        base_date = date(2024, 10, 22)
        for i in range(count):
            home_id, away_id = random.sample(team_ids, 2)
            home_profile = id_to_profile.get(home_id, (3, 3))
            away_profile = id_to_profile.get(away_id, (3, 3))

            home_base = 105 + home_profile[1] * 3
            away_base = 105 + away_profile[1] * 3
            home_score = random.randint(home_base - 8, home_base + 15)
            away_score = random.randint(away_base - 8, away_base + 15)
            if home_score == away_score:
                home_score += random.choice([-1, 1]) if random.random() > 0.5 else 1

            gr = GameRecord(
                nba_game_id=f"00224{i:06d}",
                season=SEASON,
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
    logger.info("=" * 50)
    logger.info("NBA种子数据生成开始")
    logger.info("=" * 50)

    seed_players()
    seed_player_data()
    seed_team_data()
    seed_games()

    logger.info("=" * 50)
    logger.info("种子数据生成完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
