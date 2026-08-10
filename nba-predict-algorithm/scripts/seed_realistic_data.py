"""
生成真实 NBA 样本数据 (用于 API 不可用时的开发/演示)

基于 2022-2025 真实 NBA 数据生成:
- 30 支球队 + 4 赛季数据
- ~450 名球员 + 高阶数据
- ~5000 条比赛记录
"""
import sys
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, Team, TeamData, GameRecord

random.seed(42)

# ── NBA 30 支球队 ──────────────────────────────────────────
NBA_TEAMS = [
    (1610612737, "亚特兰大老鹰", "Atlanta Hawks", "ATL", "East", "Southeast"),
    (1610612738, "波士顿凯尔特人", "Boston Celtics", "BOS", "East", "Atlantic"),
    (1610612751, "布鲁克林篮网", "Brooklyn Nets", "BKN", "East", "Atlantic"),
    (1610612766, "夏洛特黄蜂", "Charlotte Hornets", "CHA", "East", "Southeast"),
    (1610612741, "芝加哥公牛", "Chicago Bulls", "CHI", "East", "Central"),
    (1610612739, "克利夫兰骑士", "Cleveland Cavaliers", "CLE", "East", "Central"),
    (1610612742, "达拉斯独行侠", "Dallas Mavericks", "DAL", "West", "Southwest"),
    (1610612743, "丹佛掘金", "Denver Nuggets", "DEN", "West", "Northwest"),
    (1610612765, "底特律活塞", "Detroit Pistons", "DET", "East", "Central"),
    (1610612744, "金州勇士", "Golden State Warriors", "GSW", "West", "Pacific"),
    (1610612745, "休斯顿火箭", "Houston Rockets", "HOU", "West", "Southwest"),
    (1610612754, "印第安纳步行者", "Indiana Pacers", "IND", "East", "Central"),
    (1610612746, "洛杉矶快船", "LA Clippers", "LAC", "West", "Pacific"),
    (1610612747, "洛杉矶湖人", "Los Angeles Lakers", "LAL", "West", "Pacific"),
    (1610612763, "孟菲斯灰熊", "Memphis Grizzlies", "MEM", "West", "Southwest"),
    (1610612748, "迈阿密热火", "Miami Heat", "MIA", "East", "Southeast"),
    (1610612749, "密尔沃基雄鹿", "Milwaukee Bucks", "MIL", "East", "Central"),
    (1610612750, "明尼苏达森林狼", "Minnesota Timberwolves", "MIN", "West", "Northwest"),
    (1610612740, "新奥尔良鹈鹕", "New Orleans Pelicans", "NOP", "West", "Southwest"),
    (1610612752, "纽约尼克斯", "New York Knicks", "NYK", "East", "Atlantic"),
    (1610612760, "俄克拉荷马雷霆", "Oklahoma City Thunder", "OKC", "West", "Northwest"),
    (1610612753, "奥兰多魔术", "Orlando Magic", "ORL", "East", "Southeast"),
    (1610612755, "费城76人", "Philadelphia 76ers", "PHI", "East", "Atlantic"),
    (1610612756, "菲尼克斯太阳", "Phoenix Suns", "PHX", "West", "Pacific"),
    (1610612757, "波特兰开拓者", "Portland Trail Blazers", "POR", "West", "Northwest"),
    (1610612758, "萨克拉门托国王", "Sacramento Kings", "SAC", "West", "Pacific"),
    (1610612759, "圣安东尼奥马刺", "San Antonio Spurs", "SAS", "West", "Southwest"),
    (1610612761, "多伦多猛龙", "Toronto Raptors", "TOR", "East", "Atlantic"),
    (1610612762, "犹他爵士", "Utah Jazz", "UTA", "West", "Northwest"),
    (1610612764, "华盛顿奇才", "Washington Wizards", "WAS", "East", "Southeast"),
]

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]

# ── 真实球员模板 ──────────────────────────────────────────
PLAYER_TEMPLATES = [
    ("LeBron James", "SF", 1, (25, 30), (7, 8), (7, 9), 0.54, 0.36, 0.75, 28.0, 32.0, 18),
    ("Stephen Curry", "PG", 1, (26, 32), (4, 5), (5, 7), 0.47, 0.42, 0.91, 24.0, 28.0, 15),
    ("Kevin Durant", "SF", 1, (27, 30), (6, 7), (4, 6), 0.53, 0.38, 0.88, 26.0, 30.0, 16),
    ("Giannis Antetokounmpo", "PF", 1, (28, 32), (11, 13), (5, 7), 0.55, 0.28, 0.65, 29.0, 33.0, 11),
    ("Nikola Jokic", "C", 1, (24, 28), (11, 13), (9, 11), 0.58, 0.35, 0.82, 28.0, 32.0, 9),
    ("Joel Embiid", "C", 1, (28, 34), (10, 12), (3, 5), 0.50, 0.33, 0.85, 28.0, 33.0, 9),
    ("Luka Doncic", "PG", 1, (28, 34), (8, 9), (8, 10), 0.49, 0.35, 0.75, 28.0, 35.0, 6),
    ("Jayson Tatum", "SF", 1, (26, 30), (8, 9), (4, 6), 0.47, 0.37, 0.83, 26.0, 30.0, 7),
    ("Anthony Davis", "PF", 1, (24, 28), (10, 12), (3, 4), 0.52, 0.28, 0.79, 28.0, 32.0, 11),
    ("Shai Gilgeous-Alexander", "SG", 1, (28, 32), (5, 6), (6, 8), 0.51, 0.35, 0.87, 27.0, 31.0, 5),
    ("Ja Morant", "PG", 2, (22, 27), (5, 6), (7, 9), 0.47, 0.32, 0.76, 24.0, 28.0, 5),
    ("Trae Young", "PG", 2, (25, 28), (3, 4), (9, 11), 0.44, 0.36, 0.88, 26.0, 30.0, 6),
    ("Damian Lillard", "PG", 2, (25, 30), (4, 5), (6, 8), 0.46, 0.37, 0.90, 26.0, 30.0, 13),
    ("Devin Booker", "SG", 2, (25, 28), (4, 5), (5, 7), 0.48, 0.36, 0.87, 24.0, 28.0, 9),
    ("Anthony Edwards", "SG", 2, (24, 28), (5, 6), (4, 6), 0.46, 0.36, 0.78, 24.0, 28.0, 4),
    ("Donovan Mitchell", "SG", 2, (24, 28), (4, 5), (4, 6), 0.46, 0.37, 0.85, 24.0, 28.0, 7),
    ("Paolo Banchero", "PF", 2, (22, 26), (6, 8), (4, 6), 0.46, 0.33, 0.74, 24.0, 28.0, 2),
    ("Tyrese Haliburton", "PG", 2, (20, 24), (3, 4), (10, 12), 0.48, 0.38, 0.85, 22.0, 26.0, 4),
    ("Jalen Brunson", "PG", 2, (24, 28), (3, 4), (6, 8), 0.47, 0.38, 0.83, 24.0, 28.0, 7),
    ("Jaylen Brown", "SF", 2, (23, 27), (5, 6), (3, 5), 0.49, 0.35, 0.76, 24.0, 28.0, 8),
    ("Pascal Siakam", "PF", 3, (20, 24), (6, 8), (4, 6), 0.48, 0.32, 0.77, 22.0, 26.0, 9),
    ("Bam Adebayo", "C", 3, (18, 22), (9, 11), (4, 6), 0.53, 0.15, 0.80, 22.0, 26.0, 7),
    ("De'Aaron Fox", "PG", 3, (22, 26), (4, 5), (6, 8), 0.47, 0.32, 0.74, 22.0, 26.0, 7),
    ("Scottie Barnes", "PF", 3, (18, 22), (7, 9), (5, 7), 0.47, 0.30, 0.75, 22.0, 26.0, 3),
    ("Evan Mobley", "PF", 3, (16, 20), (8, 10), (3, 5), 0.52, 0.25, 0.72, 22.0, 26.0, 3),
    ("Desmond Bane", "SG", 3, (20, 24), (4, 5), (4, 6), 0.47, 0.39, 0.87, 22.0, 26.0, 5),
    ("Mikal Bridges", "SF", 3, (18, 22), (4, 5), (3, 5), 0.47, 0.37, 0.84, 22.0, 26.0, 7),
    ("Franz Wagner", "SF", 3, (20, 24), (5, 6), (4, 6), 0.47, 0.33, 0.85, 22.0, 26.0, 3),
    ("Alperen Sengun", "C", 3, (18, 22), (9, 11), (5, 7), 0.53, 0.28, 0.70, 22.0, 26.0, 3),
    ("Jaren Jackson Jr.", "PF", 3, (20, 24), (5, 7), (1, 2), 0.47, 0.35, 0.78, 22.0, 26.0, 5),
    ("Mike Conley", "PG", 4, (10, 14), (3, 4), (5, 7), 0.44, 0.38, 0.85, 16.0, 20.0, 17),
    ("Chris Paul", "PG", 4, (10, 14), (4, 5), (7, 9), 0.44, 0.35, 0.83, 16.0, 20.0, 19),
    ("Klay Thompson", "SG", 4, (15, 20), (3, 4), (2, 3), 0.43, 0.39, 0.88, 18.0, 22.0, 13),
    ("Draymond Green", "PF", 4, (8, 12), (6, 8), (5, 7), 0.48, 0.30, 0.70, 18.0, 22.0, 12),
    ("Brook Lopez", "C", 4, (12, 16), (4, 6), (1, 2), 0.50, 0.36, 0.80, 16.0, 20.0, 15),
    ("Jrue Holiday", "SG", 4, (14, 18), (5, 6), (5, 7), 0.48, 0.36, 0.80, 18.0, 22.0, 14),
    ("Marcus Smart", "PG", 4, (12, 16), (3, 4), (5, 7), 0.42, 0.34, 0.78, 18.0, 22.0, 9),
    ("Derrick White", "SG", 4, (14, 18), (3, 4), (4, 6), 0.45, 0.38, 0.85, 18.0, 22.0, 6),
    ("Aaron Gordon", "PF", 4, (12, 16), (5, 7), (2, 4), 0.52, 0.30, 0.70, 18.0, 22.0, 10),
    ("Jordan Clarkson", "SG", 5, (14, 18), (3, 4), (3, 5), 0.43, 0.34, 0.82, 16.0, 20.0, 10),
    ("Tyler Herro", "SG", 5, (18, 22), (4, 5), (4, 6), 0.44, 0.37, 0.87, 18.0, 22.0, 5),
    ("Malik Monk", "SG", 5, (12, 16), (3, 4), (3, 5), 0.44, 0.36, 0.83, 16.0, 20.0, 6),
    ("Duncan Robinson", "SF", 5, (10, 14), (2, 3), (1, 2), 0.42, 0.40, 0.88, 14.0, 18.0, 6),
    ("Buddy Hield", "SG", 5, (12, 16), (3, 4), (2, 3), 0.43, 0.40, 0.85, 16.0, 20.0, 9),
    ("Bobby Portis", "PF", 5, (12, 16), (7, 9), (1, 2), 0.47, 0.36, 0.78, 16.0, 20.0, 8),
    ("Josh Hart", "SF", 5, (8, 12), (7, 9), (3, 5), 0.48, 0.34, 0.76, 16.0, 20.0, 7),
    ("Nic Claxton", "C", 5, (10, 14), (7, 9), (2, 3), 0.60, 0.00, 0.55, 16.0, 20.0, 4),
    ("Austin Reaves", "SG", 5, (14, 18), (4, 5), (5, 7), 0.47, 0.37, 0.85, 16.0, 20.0, 3),
]

GENERIC_NAMES = [
    "James Johnson", "Robert Smith", "Michael Brown", "David Wilson",
    "Thomas Anderson", "Chris Taylor", "Kevin Martin", "Brian Thompson",
    "Daniel White", "Jason Harris", "Ryan Clark", "Matt Lewis",
    "Tim Walker", "Jeff Hall", "Greg Allen", "Steve Young",
    "Paul King", "Mark Wright", "Luke Scott", "Jake Green",
    "Sam Baker", "Ben Cooper", "Dan Reed", "Pat Kelly",
    "Alex Howard", "Nick Price", "Tom Gray", "Jim Bell",
    "Joe Cox", "Ray Ward", "Max Wood", "Ian Cole",
    "Sean Hill", "Adam Fox", "Eric Long", "Kyle Ross",
    "Noah West", "Liam Day", "Ethan Hale", "Owen Moon",
    "Mason Lake", "Lucas Reid", "Henry Nash", "Jack Hunt",
    "Aiden Moss", "Ryan Bird", "Dylan Ford", "Tyler Rice",
]


def _rand_stat(low, high):
    return round(random.uniform(low, high), 1)


def _rand_pct(low, high):
    return round(random.uniform(low, high), 3)


def seed_teams(db):
    """确保 30 支球队存在"""
    existing = {t.nba_id: t for t in db.query(Team).all()}
    added = 0
    for nba_id, cn_name, en_name, abbr, conf, div in NBA_TEAMS:
        if str(nba_id) not in existing and nba_id not in existing:
            db.add(Team(
                nba_id=str(nba_id),
                team_name=cn_name,
                team_name_en=en_name,
                abbreviation=abbr,
                conference=conf,
                division=div,
                status=1,
            ))
            added += 1
    db.commit()
    logger.info(f"球队: 新增 {added}, 总计 {len(NBA_TEAMS)}")
    return {str(t.nba_id): t for t in db.query(Team).all()}


def _generate_team_strength():
    """生成球队实力参数"""
    tier = random.choices([1, 2, 3, 4], weights=[0.10, 0.25, 0.40, 0.25])[0]
    if tier == 1:
        win_pct = random.uniform(0.62, 0.78)
        off_rtg = random.uniform(114, 120)
        def_rtg = random.uniform(106, 110)
    elif tier == 2:
        win_pct = random.uniform(0.50, 0.62)
        off_rtg = random.uniform(111, 116)
        def_rtg = random.uniform(109, 113)
    elif tier == 3:
        win_pct = random.uniform(0.40, 0.55)
        off_rtg = random.uniform(109, 114)
        def_rtg = random.uniform(111, 115)
    else:
        win_pct = random.uniform(0.25, 0.42)
        off_rtg = random.uniform(106, 112)
        def_rtg = random.uniform(113, 118)
    return win_pct, off_rtg, def_rtg


def seed_players_and_data(db, team_map, season):
    """生成一个赛季的球员和球员数据"""
    team_list = list(team_map.values())
    name_idx = 0
    added_players = 0
    added_data = 0

    existing_players = {p.nba_id: p for p in db.query(Player).all()}

    for team in team_list:
        roster = []
        n_stars = random.randint(0, 2)
        shuffled_templates = PLAYER_TEMPLATES.copy()
        random.shuffle(shuffled_templates)

        for i in range(min(10, 15)):
            if i < n_stars and i < len(shuffled_templates):
                roster.append(("star", shuffled_templates[i]))
            elif i < len(shuffled_templates):
                roster.append(("template", shuffled_templates[i]))
            else:
                roster.append(("generic", None))

        while len(roster) < 15:
            roster.append(("generic", None))

        for idx, (ptype, template) in enumerate(roster):
            is_starter = idx < 5

            if template:
                name, pos, tier, ppg_r, rpg_r, apg_r, fg_pct, tfg_pct, ft_pct, usg, per, exp = template
                player_name = name
                nba_id = str(hash(f"{name}_{team.team_id}_{season}") % 10000000)
            else:
                player_name = GENERIC_NAMES[name_idx % len(GENERIC_NAMES)]
                name_idx += 1
                nba_id = str(hash(f"{player_name}_{team.team_id}_{season}") % 10000000)
                pos = random.choice(["PG", "SG", "SF", "PF", "C"])
                tier = 5
                ppg_r = (5, 12) if is_starter else (2, 8)
                rpg_r = (2, 5) if pos not in ("C", "PF") else (4, 8)
                apg_r = (1, 5) if pos in ("PG", "SG") else (1, 3)
                fg_pct = random.uniform(0.40, 0.48)
                tfg_pct = random.uniform(0.30, 0.38)
                ft_pct = random.uniform(0.65, 0.82)
                usg = random.uniform(12, 20)
                per = random.uniform(10, 16)
                exp = random.randint(0, 8)

            if nba_id in existing_players:
                player = existing_players[nba_id]
            else:
                player = Player(
                    nba_id=nba_id,
                    player_name=player_name,
                    player_name_en=player_name,
                    team_id=team.team_id,
                    position=pos,
                    experience=exp,
                    status=1,
                )
                db.add(player)
                db.flush()
                existing_players[nba_id] = player
                added_players += 1

            gp = random.randint(55, 82) if tier <= 3 else random.randint(30, 75)
            gs = gp if is_starter else random.randint(0, int(gp * 0.3))
            mpg = _rand_stat(28, 36) if is_starter else _rand_stat(12, 24)

            tier_mult = {1: 1.0, 2: 0.85, 3: 0.70, 4: 0.55, 5: 0.40}[tier]
            ppg = max(0, _rand_stat(*ppg_r) * tier_mult + random.uniform(-1, 1))
            rpg = max(0, _rand_stat(*rpg_r) * tier_mult + random.uniform(-0.5, 0.5))
            apg = max(0, _rand_stat(*apg_r) * tier_mult + random.uniform(-0.5, 0.5))
            stl = max(0, _rand_stat(0.5, 1.5) * tier_mult)
            blk = max(0, _rand_stat(0.3, 1.2) * tier_mult if pos in ("C", "PF") else _rand_stat(0.2, 0.6))
            tov = max(0, _rand_stat(1.0, 3.0) * tier_mult)
            fg_m = ppg / 2.0 * random.uniform(0.4, 0.5)
            fg_a = fg_m / max(fg_pct, 0.35)
            tfg_m = max(0, random.uniform(0.8, 2.5) * tier_mult)
            tfg_a = tfg_m / max(tfg_pct, 0.30)
            ft_m = max(0, random.uniform(1.5, 4.0) * tier_mult)
            ft_a = ft_m / max(ft_pct, 0.60)

            ts_pct = (ppg / (2 * (fg_a + 0.44 * ft_a))) if (fg_a + ft_a) > 0 else 0.50
            ts_pct = min(0.70, max(0.45, ts_pct))

            off_rtg = _rand_stat(105, 120) if tier <= 3 else _rand_stat(100, 115)
            def_rtg = _rand_stat(106, 115)
            net_rtg = off_rtg - def_rtg
            ast_pct = min(40, apg * 3.5 + random.uniform(0, 5))
            reb_pct = min(30, rpg * 2.0 + random.uniform(0, 3))
            stl_pct = stl * 1.5 + random.uniform(0, 0.5)
            blk_pct = blk * 2.0 + random.uniform(0, 0.5) if pos in ("C", "PF") else blk * 1.5
            tov_pct = tov * 3.0 + random.uniform(5, 12)
            efg_pct = (fg_m + 0.5 * tfg_m) / max(fg_a, 1)
            cv = random.uniform(0.15, 0.45) if tier <= 3 else random.uniform(0.20, 0.55)

            pd = PlayerData(
                player_id=player.player_id,
                season=season,
                team_id=team.team_id,
                games_played=gp,
                games_started=gs,
                minutes_per_game=round(mpg, 1),
                points_per_game=round(ppg, 1),
                rebounds_per_game=round(rpg, 1),
                assists_per_game=round(apg, 1),
                steals_per_game=round(stl, 1),
                blocks_per_game=round(blk, 1),
                turnovers_per_game=round(tov, 1),
                fg_made_per_game=round(fg_m, 1),
                fg_attempted_per_game=round(fg_a, 1),
                fg_percentage=round(fg_pct, 3),
                three_made_per_game=round(tfg_m, 1),
                three_attempted_per_game=round(tfg_a, 1),
                three_percentage=round(tfg_pct, 3),
                ft_made_per_game=round(ft_m, 1),
                ft_attempted_per_game=round(ft_a, 1),
                ft_percentage=round(ft_pct, 3),
                per=round(per, 1),
                true_shooting_pct=round(ts_pct, 3),
                usage_rate=round(usg, 1),
                win_shares=round(random.uniform(0, 8), 1),
                bpm=round(random.uniform(-3, 6), 1),
                vorp=round(random.uniform(-0.5, 4), 1),
                offensive_rating=round(off_rtg, 1),
                defensive_rating=round(def_rtg, 1),
                net_rating=round(net_rtg, 1),
                assist_pct=round(ast_pct, 1),
                rebound_pct=round(reb_pct, 1),
                steal_pct=round(stl_pct, 1),
                block_pct=round(blk_pct, 1),
                turnover_pct=round(tov_pct, 1),
                effective_fg_pct=round(efg_pct, 3),
                points_cv=round(cv, 3),
            )
            db.add(pd)
            added_data += 1

    db.commit()
    logger.info(f"  [{season}] 球员: 新增 {added_players}, 数据: {added_data}")


def seed_team_data(db, team_map, season):
    """生成一个赛季的球队数据"""
    existing = {(td.team_id, td.season) for td in db.query(TeamData).filter(TeamData.season == season).all()}
    added = 0
    for team in team_map.values():
        if (team.team_id, season) in existing:
            continue
        win_pct, off_rtg, def_rtg = _generate_team_strength()
        pace = _rand_stat(96, 104)
        ppg = _rand_stat(108, 120)
        oppg = ppg - (off_rtg - def_rtg) * 0.8
        wins = int(win_pct * 82)
        losses = 82 - wins

        td = TeamData(
            team_id=team.team_id,
            season=season,
            wins=wins,
            losses=losses,
            win_percentage=round(win_pct, 3),
            points_per_game=round(ppg, 1),
            opponent_points=round(oppg, 1),
            assists_per_game=round(_rand_stat(22, 28), 1),
            rebounds_per_game=round(_rand_stat(42, 48), 1),
            turnovers_per_game=round(_rand_stat(12, 16), 1),
            pace=round(pace, 1),
            offensive_rating=round(off_rtg, 1),
            defensive_rating=round(def_rtg, 1),
            net_rating=round(off_rtg - def_rtg, 1),
            assist_pct=round(_rand_stat(55, 68), 1),
            rebound_pct=round(_rand_stat(48, 54), 1),
            effective_fg_pct=round(_rand_pct(0.50, 0.57), 3),
            true_shooting_pct=round(_rand_pct(0.55, 0.62), 3),
        )
        db.add(td)
        added += 1
    db.commit()
    logger.info(f"  [{season}] 球队数据: {added}")


def seed_game_records(db, team_map, season):
    """生成一个赛季的比赛记录"""
    team_list = list(team_map.values())
    added = 0
    year = int(season.split("-")[0])

    for game_num in range(41):
        random.shuffle(team_list)
        for i in range(0, 30, 2):
            home = team_list[i]
            away = team_list[i + 1]

            home_td = db.query(TeamData).filter_by(team_id=home.team_id, season=season).first()
            away_td = db.query(TeamData).filter_by(team_id=away.team_id, season=season).first()

            home_base = home_td.points_per_game if home_td else 112
            away_base = away_td.points_per_game if away_td else 112

            home_score = int(home_base + random.uniform(-8, 8) + 2)
            away_score = int(away_base + random.uniform(-8, 8))

            if home_score == away_score:
                home_score += random.choice([1, 2, 3])

            score_diff = home_score - away_score
            total_score = home_score + away_score
            home_win = 1 if home_score > away_score else 0

            month = random.randint(10, 12)
            day = random.randint(1, 28)
            game_date = datetime(year, month, day)

            gr = GameRecord(
                nba_game_id=f"{season[-2:]}_{home.nba_id[-4:]}_{away.nba_id[-4:]}_{game_num}",
                season=season,
                game_date=game_date,
                game_type="regular",
                home_team_id=home.team_id,
                away_team_id=away.team_id,
                home_score=home_score,
                away_score=away_score,
                home_win=home_win,
                score_diff=score_diff,
                total_score=total_score,
                is_playoff=0,
                status="FINISHED",
            )
            db.add(gr)
            added += 1

    db.commit()
    logger.info(f"  [{season}] 比赛记录: {added}")


def run():
    logger.info("=" * 50)
    logger.info("NBA 样本数据生成开始")
    logger.info("=" * 50)

    with SessionLocal() as db:
        team_map = seed_teams(db)

        for season in SEASONS:
            logger.info(f"\n--- {season} ---")
            seed_players_and_data(db, team_map, season)
            seed_team_data(db, team_map, season)
            seed_game_records(db, team_map, season)

    logger.info("\n" + "=" * 50)
    logger.info("样本数据生成完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
