"""
SQLAlchemy ORM模型 - 映射数据库表
"""
from sqlalchemy import Column, BigInteger, String, Integer, Float, Date, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class Player(Base):
    __tablename__ = "player"
    player_id = Column(BigInteger, primary_key=True, autoincrement=True)
    nba_id = Column(String(20))
    player_name = Column(String(100))
    player_name_en = Column(String(100))
    position = Column(String(10))
    jersey_number = Column(Integer)
    team_id = Column(BigInteger)
    birth_date = Column(Date)
    age = Column(Integer)
    height = Column(Float)
    weight = Column(Float)
    draft_year = Column(Integer)
    draft_round = Column(Integer)
    draft_pick = Column(Integer)
    experience = Column(Integer)
    all_star_count = Column(Integer, default=0)
    all_star_last = Column(Integer)
    injury_status = Column(String(20), default="HEALTHY")
    injury_type = Column(String(100))
    injury_date = Column(Date)
    player_type = Column(String(50))
    cluster_id = Column(Integer)
    cluster_name = Column(String(50))
    status = Column(Integer, default=1)
    # 球员角色与影响力
    player_role = Column(String(30))          # ball_handler / defensive_anchor / scorer / two_way / stretch_big / rim_protector / floor_general / sixth_man / three_and_d / connector / energy_big / microwave_scorer / spot_up_shooter / veteran_stabilizer / role_player
    impact_score = Column(Float)              # 综合影响力 (0-100)
    offensive_impact = Column(Float)          # 进攻影响力 (0-1)
    defensive_impact = Column(Float)          # 防守影响力 (0-1)
    team_dependency = Column(Float)           # 球队依赖度 (0-1), 该球员占球队产出的比例
    stability_score = Column(Float)           # 稳定性 (0-1), 低波动+高出勤 = 高稳定
    connector_score = Column(Float)           # 组织串联值 (0-1), 不占球权但能组织进攻
    veteran_score = Column(Float)             # 经验值 (0-1), 老将的隐性价值


class PlayerData(Base):
    __tablename__ = "player_data"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger)
    season = Column(String(10))
    team_id = Column(BigInteger)
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    minutes_per_game = Column(Float, default=0)
    points_per_game = Column(Float, default=0)
    rebounds_per_game = Column(Float, default=0)
    assists_per_game = Column(Float, default=0)
    steals_per_game = Column(Float, default=0)
    blocks_per_game = Column(Float, default=0)
    turnovers_per_game = Column(Float, default=0)
    fg_made_per_game = Column(Float, default=0)
    fg_attempted_per_game = Column(Float, default=0)
    fg_percentage = Column(Float, default=0)
    three_made_per_game = Column(Float, default=0)
    three_attempted_per_game = Column(Float, default=0)
    three_percentage = Column(Float, default=0)
    ft_made_per_game = Column(Float, default=0)
    ft_attempted_per_game = Column(Float, default=0)
    ft_percentage = Column(Float, default=0)
    per = Column(Float)
    true_shooting_pct = Column(Float)
    usage_rate = Column(Float)
    win_shares = Column(Float)
    bpm = Column(Float)
    vorp = Column(Float)
    isolation_pct = Column(Float)
    pick_roll_pct = Column(Float)
    spot_up_pct = Column(Float)
    post_up_pct = Column(Float)
    points_std = Column(Float)
    points_cv = Column(Float)
    vs_pg_efficiency = Column(Float)
    vs_sg_efficiency = Column(Float)
    vs_sf_efficiency = Column(Float)
    vs_pf_efficiency = Column(Float)
    vs_c_efficiency = Column(Float)
    # 高阶数据 (nba_api Advanced)
    offensive_rating = Column(Float)
    defensive_rating = Column(Float)
    net_rating = Column(Float)
    assist_pct = Column(Float)
    rebound_pct = Column(Float)
    steal_pct = Column(Float)
    block_pct = Column(Float)
    turnover_pct = Column(Float)
    effective_fg_pct = Column(Float)


class Team(Base):
    __tablename__ = "team"
    team_id = Column(BigInteger, primary_key=True, autoincrement=True)
    nba_id = Column(String(20))
    team_name = Column(String(50))
    team_name_en = Column(String(50))
    abbreviation = Column(String(10))
    conference = Column(String(10))
    division = Column(String(20))
    city = Column(String(50))
    arena = Column(String(100))
    defense_type = Column(String(50))
    offense_type = Column(String(50))
    defense_cluster = Column(Integer)
    offense_cluster = Column(Integer)
    strength_level = Column(String(20))
    strength_score = Column(Float)
    tag_resilience = Column(Integer, default=0)
    tag_slow_start = Column(Integer, default=0)
    tag_core_depend = Column(Integer, default=0)
    home_win_rate = Column(Float)
    away_win_rate = Column(Float)
    status = Column(Integer, default=1)


class TeamData(Base):
    __tablename__ = "team_data"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id = Column(BigInteger)
    season = Column(String(10))
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_percentage = Column(Float, default=0)
    home_wins = Column(Integer, default=0)
    home_losses = Column(Integer, default=0)
    away_wins = Column(Integer, default=0)
    away_losses = Column(Integer, default=0)
    points_per_game = Column(Float, default=0)
    assists_per_game = Column(Float, default=0)
    rebounds_per_game = Column(Float, default=0)
    offensive_rebounds = Column(Float, default=0)
    turnovers_per_game = Column(Float, default=0)
    fg_percentage = Column(Float, default=0)
    three_percentage = Column(Float, default=0)
    ft_percentage = Column(Float, default=0)
    pace = Column(Float)
    offensive_rating = Column(Float)
    opponent_points = Column(Float, default=0)
    opponent_fg_percentage = Column(Float)
    opponent_three_pct = Column(Float)
    defensive_rating = Column(Float)
    steals_per_game = Column(Float, default=0)
    blocks_per_game = Column(Float, default=0)
    fast_break_points = Column(Float)
    points_in_paint = Column(Float)
    second_chance_points = Column(Float)
    bench_points = Column(Float)
    points_std = Column(Float)
    points_cv = Column(Float)
    recent_win_rate = Column(Float)
    momentum = Column(Float)
    home_ppg = Column(Float)
    away_ppg = Column(Float)
    # 高阶数据 (nba_api Advanced)
    net_rating = Column(Float)
    assist_pct = Column(Float)
    rebound_pct = Column(Float)
    effective_fg_pct = Column(Float)
    true_shooting_pct = Column(Float)


class GameRecord(Base):
    __tablename__ = "game_record"
    game_id = Column(BigInteger, primary_key=True, autoincrement=True)
    nba_game_id = Column(String(30))
    season = Column(String(10))
    game_date = Column(Date)
    game_type = Column(String(20))
    home_team_id = Column(BigInteger)
    away_team_id = Column(BigInteger)
    home_score = Column(Integer)
    away_score = Column(Integer)
    home_win = Column(Integer)
    score_diff = Column(Integer)
    total_score = Column(Integer)
    is_playoff = Column(Integer, default=0)
    status = Column(String(20), default="FINISHED")
    home_q1_score = Column(Integer)
    home_q2_score = Column(Integer)
    home_q3_score = Column(Integer)
    home_q4_score = Column(Integer)
    away_q1_score = Column(Integer)
    away_q2_score = Column(Integer)
    away_q3_score = Column(Integer)
    away_q4_score = Column(Integer)
    overtime = Column(String(20))
    playoff_round = Column(String(20))
    series_id = Column(BigInteger)


class PlayerRoster(Base):
    __tablename__ = "player_roster"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger)
    team_id = Column(BigInteger)
    season = Column(String(10))
    position = Column(String(10))
    jersey_number = Column(Integer)
    height = Column(Float)
    weight = Column(Float)
    age = Column(Integer)
    experience = Column(Integer)
    games_played = Column(Integer)


class InjuryRecord(Base):
    __tablename__ = "injury_record"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger)
    team_id = Column(BigInteger)
    season = Column(String(10))
    injury_date = Column(Date)
    return_date = Column(Date)
    games_missed = Column(Integer)
    body_part = Column(String(50))
    description = Column(String(200))
    source = Column(String(30))


class BattleRecord(Base):
    __tablename__ = "battle_record"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    team1_id = Column(BigInteger)
    team2_id = Column(BigInteger)
    season = Column(String(10))
    total_games = Column(Integer, default=0)
    team1_wins = Column(Integer, default=0)
    team2_wins = Column(Integer, default=0)
    team1_avg_score = Column(Float)
    team2_avg_score = Column(Float)
    avg_score_diff = Column(Float)


class OddsData(Base):
    __tablename__ = "odds_data"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(BigInteger)
    game_date = Column(Date)
    home_team_id = Column(BigInteger)
    away_team_id = Column(BigInteger)
    source_id = Column(BigInteger)
    home_win_odds = Column(Float)
    away_win_odds = Column(Float)
    home_win_prob = Column(Float)
    away_win_prob = Column(Float)
    handicap_line = Column(Float)
    total_line = Column(Float)
    home_win_coeff = Column(Float)
    away_win_coeff = Column(Float)
    total_coeff = Column(Float)
    diff_coeff = Column(Float)
    data_quality = Column(String(20), default="NORMAL")


class OddsSource(Base):
    __tablename__ = "odds_source"
    source_id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_name = Column(String(50))
    source_code = Column(String(20))
    source_url = Column(String(200))
    source_type = Column(String(20))
    mae_score = Column(Float)
    calibration_score = Column(Float)
    completeness_score = Column(Float)
    timeliness_score = Column(Float)
    stability_score = Column(Float)
    total_score = Column(Float)
    priority = Column(Integer, default=0)
    is_primary = Column(Integer, default=0)
    status = Column(String(20), default="ACTIVE")


class SystemConfig(Base):
    __tablename__ = "system_config"
    config_id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_group = Column(String(50))
    config_key = Column(String(100))
    config_value = Column(String(500))
    config_type = Column(String(20), default="STRING")
    description = Column(String(200))
    min_value = Column(Float)
    max_value = Column(Float)
    default_value = Column(String(500))
    is_system = Column(Integer, default=0)


class AlgorithmParamSnapshot(Base):
    __tablename__ = "algorithm_param_snapshot"
    snapshot_id = Column(BigInteger, primary_key=True, autoincrement=True)
    version = Column(String(20))
    param_json = Column(JSON)
    description = Column(String(200))
    mae_score = Column(Float)
    is_current = Column(Integer, default=0)
    create_time = Column(DateTime, server_default=func.now())


class SeriesStar(Base):
    __tablename__ = "series_star"
    star_id = Column(BigInteger, primary_key=True, autoincrement=True)
    series_id = Column(BigInteger)
    player_id = Column(BigInteger)
    team_id = Column(BigInteger)
    opponent_team_id = Column(BigInteger)
    season = Column(String(10))
    avg_score = Column(Float)
    avg_fg_pct = Column(Float)
    score_up = Column(Float)
    hit_rate_up = Column(Float)
    judge_threshold_score = Column(Float, default=5.0)
    judge_threshold_pct = Column(Float, default=0.10)
    is_star = Column(Integer, default=0)
    key_game_id = Column(BigInteger)
    key_game_score = Column(Integer)
    key_game_fg_pct = Column(Float)
