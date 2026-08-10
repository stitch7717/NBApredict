-- ============================================================
-- NBA球员与球队表现预测系统 - 数据库初始化脚本
-- 数据库: MySQL 8.0
-- 字符集: utf8mb4
-- 创建时间: 2026-05-01
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS nba_predict DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE nba_predict;

-- ============================================================
-- 1. 球员基础信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS player (
    player_id       BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '球员ID',
    nba_id          VARCHAR(20) NOT NULL COMMENT 'NBA官方球员ID',
    player_name     VARCHAR(100) NOT NULL COMMENT '球员姓名',
    player_name_en  VARCHAR(100) NOT NULL COMMENT '球员英文名',
    position        VARCHAR(10) NOT NULL COMMENT '位置(PG/SG/SF/PF/C)',
    jersey_number   INT COMMENT '球衣号码',
    team_id         BIGINT COMMENT '当前球队ID',
    birth_date      DATE COMMENT '出生日期',
    age             INT COMMENT '年龄',
    height          DECIMAL(5,2) COMMENT '身高(cm)',
    weight          DECIMAL(5,2) COMMENT '体重(kg)',
    draft_year      INT COMMENT '选秀年份',
    draft_round     INT COMMENT '选秀轮次',
    draft_pick      INT COMMENT '选秀顺位',
    experience      INT COMMENT 'NBA赛季数',
    all_star_count  INT DEFAULT 0 COMMENT '全明星次数',
    all_star_last   INT COMMENT '最近一次全明星年份',
    injury_status   VARCHAR(20) DEFAULT 'HEALTHY' COMMENT '伤病状态(HEALTHY/INJURED/RECOVERY)',
    injury_type     VARCHAR(100) COMMENT '伤病类型',
    injury_date     DATE COMMENT '伤病日期',
    player_type     VARCHAR(50) COMMENT '球员类型标签(老将/新星/全明星等)',
    cluster_id      INT COMMENT '聚类分类ID',
    cluster_name    VARCHAR(50) COMMENT '聚类分类名称',
    status          TINYINT DEFAULT 1 COMMENT '状态(1-现役 0-退役)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_nba_id (nba_id),
    KEY idx_team_id (team_id),
    KEY idx_position (position),
    KEY idx_cluster (cluster_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球员基础信息表';

-- ============================================================
-- 2. 球员赛季数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS player_data (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    player_id       BIGINT NOT NULL COMMENT '球员ID',
    season          VARCHAR(10) NOT NULL COMMENT '赛季(如2025-26)',
    team_id         BIGINT NOT NULL COMMENT '球队ID',
    games_played    INT DEFAULT 0 COMMENT '出场数',
    games_started   INT DEFAULT 0 COMMENT '首发数',
    minutes_per_game DECIMAL(5,2) DEFAULT 0 COMMENT '场均出场时间',
    -- 基础数据
    points_per_game     DECIMAL(5,2) DEFAULT 0 COMMENT '场均得分',
    rebounds_per_game   DECIMAL(5,2) DEFAULT 0 COMMENT '场均篮板',
    assists_per_game    DECIMAL(5,2) DEFAULT 0 COMMENT '场均助攻',
    steals_per_game     DECIMAL(5,2) DEFAULT 0 COMMENT '场均抢断',
    blocks_per_game     DECIMAL(5,2) DEFAULT 0 COMMENT '场均盖帽',
    turnovers_per_game  DECIMAL(5,2) DEFAULT 0 COMMENT '场均失误',
    fg_made_per_game    DECIMAL(5,2) DEFAULT 0 COMMENT '场均命中数',
    fg_attempted_per_game DECIMAL(5,2) DEFAULT 0 COMMENT '场均出手数',
    fg_percentage       DECIMAL(5,3) DEFAULT 0 COMMENT '投篮命中率',
    three_made_per_game DECIMAL(5,2) DEFAULT 0 COMMENT '场均三分命中',
    three_attempted_per_game DECIMAL(5,2) DEFAULT 0 COMMENT '场均三分出手',
    three_percentage    DECIMAL(5,3) DEFAULT 0 COMMENT '三分命中率',
    ft_made_per_game    DECIMAL(5,2) DEFAULT 0 COMMENT '场均罚球命中',
    ft_attempted_per_game DECIMAL(5,2) DEFAULT 0 COMMENT '场均罚球出手',
    ft_percentage       DECIMAL(5,3) DEFAULT 0 COMMENT '罚球命中率',
    -- 高阶数据
    per                 DECIMAL(5,2) COMMENT '效率值(PER)',
    true_shooting_pct   DECIMAL(5,3) COMMENT '真实命中率',
    usage_rate          DECIMAL(5,3) COMMENT '回合占有率',
    win_shares          DECIMAL(5,2) COMMENT '胜利贡献值',
    bpm                 DECIMAL(5,2) COMMENT '正负值(BPM)',
    vorp                DECIMAL(5,2) COMMENT '不可替代值(VORP)',
    -- 单打/挡拆占比
    isolation_pct       DECIMAL(5,3) COMMENT '单打占比',
    pick_roll_pct       DECIMAL(5,3) COMMENT '挡拆占比',
    spot_up_pct         DECIMAL(5,3) COMMENT '定点投篮占比',
    post_up_pct         DECIMAL(5,3) COMMENT '背身单打占比',
    -- 稳定性指标
    points_std          DECIMAL(5,2) COMMENT '得分标准差',
    points_cv           DECIMAL(5,3) COMMENT '得分变异系数',
    -- 对位数据
    vs_pg_efficiency    DECIMAL(5,2) COMMENT '对位PG效率',
    vs_sg_efficiency    DECIMAL(5,2) COMMENT '对位SG效率',
    vs_sf_efficiency    DECIMAL(5,2) COMMENT '对位SF效率',
    vs_pf_efficiency    DECIMAL(5,2) COMMENT '对位PF效率',
    vs_c_efficiency     DECIMAL(5,2) COMMENT '对位C效率',
    create_time         DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_player_season (player_id, season),
    KEY idx_season (season),
    KEY idx_team (team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球员赛季数据表';

-- ============================================================
-- 3. 球队基础信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS team (
    team_id         BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '球队ID',
    nba_id          VARCHAR(20) NOT NULL COMMENT 'NBA官方球队ID',
    team_name       VARCHAR(50) NOT NULL COMMENT '球队名称',
    team_name_en    VARCHAR(50) NOT NULL COMMENT '球队英文名',
    abbreviation    VARCHAR(10) NOT NULL COMMENT '球队缩写',
    conference      VARCHAR(10) NOT NULL COMMENT '分区(East/West)',
    division        VARCHAR(20) NOT NULL COMMENT '赛区',
    city            VARCHAR(50) COMMENT '城市',
    arena           VARCHAR(100) COMMENT '主场球馆',
    -- 风格分类
    defense_type    VARCHAR(50) COMMENT '防守体系类型',
    offense_type    VARCHAR(50) COMMENT '进攻风格类型',
    defense_cluster INT COMMENT '防守聚类ID',
    offense_cluster INT COMMENT '进攻聚类ID',
    strength_level  VARCHAR(20) COMMENT '实力等级(强/中/弱)',
    strength_score  DECIMAL(5,2) COMMENT '实力评分',
    -- 动态标签
    tag_resilience  TINYINT DEFAULT 0 COMMENT '韧性标签(0/1)',
    tag_slow_start  TINYINT DEFAULT 0 COMMENT '慢热标签(0/1)',
    tag_core_depend TINYINT DEFAULT 0 COMMENT '核心依赖标签(0/1)',
    -- 主客场数据
    home_win_rate   DECIMAL(5,3) COMMENT '主场胜率',
    away_win_rate   DECIMAL(5,3) COMMENT '客场胜率',
    status          TINYINT DEFAULT 1 COMMENT '状态(1-活跃 0-不活跃)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_nba_id (nba_id),
    UNIQUE KEY uk_abbreviation (abbreviation),
    KEY idx_conference (conference),
    KEY idx_defense_cluster (defense_cluster),
    KEY idx_offense_cluster (offense_cluster)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球队基础信息表';

-- ============================================================
-- 4. 球队赛季数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS team_data (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    team_id         BIGINT NOT NULL COMMENT '球队ID',
    season          VARCHAR(10) NOT NULL COMMENT '赛季',
    -- 战绩
    wins            INT DEFAULT 0 COMMENT '胜场',
    losses          INT DEFAULT 0 COMMENT '负场',
    win_percentage  DECIMAL(5,3) DEFAULT 0 COMMENT '胜率',
    home_wins       INT DEFAULT 0 COMMENT '主场胜场',
    home_losses     INT DEFAULT 0 COMMENT '主场负场',
    away_wins       INT DEFAULT 0 COMMENT '客场胜场',
    away_losses     INT DEFAULT 0 COMMENT '客场负场',
    -- 进攻数据
    points_per_game         DECIMAL(5,2) DEFAULT 0 COMMENT '场均得分',
    assists_per_game        DECIMAL(5,2) DEFAULT 0 COMMENT '场均助攻',
    rebounds_per_game       DECIMAL(5,2) DEFAULT 0 COMMENT '场均篮板',
    offensive_rebounds      DECIMAL(5,2) DEFAULT 0 COMMENT '场均进攻篮板',
    turnovers_per_game      DECIMAL(5,2) DEFAULT 0 COMMENT '场均失误',
    fg_percentage           DECIMAL(5,3) DEFAULT 0 COMMENT '投篮命中率',
    three_percentage        DECIMAL(5,3) DEFAULT 0 COMMENT '三分命中率',
    ft_percentage           DECIMAL(5,3) DEFAULT 0 COMMENT '罚球命中率',
    pace                    DECIMAL(5,2) COMMENT '比赛节奏',
    offensive_rating        DECIMAL(5,2) COMMENT '进攻效率',
    -- 防守数据
    opponent_points         DECIMAL(5,2) DEFAULT 0 COMMENT '对手场均得分',
    opponent_fg_percentage  DECIMAL(5,3) COMMENT '对手投篮命中率',
    opponent_three_pct      DECIMAL(5,3) COMMENT '对手三分命中率',
    defensive_rating        DECIMAL(5,2) COMMENT '防守效率',
    steals_per_game         DECIMAL(5,2) DEFAULT 0 COMMENT '场均抢断',
    blocks_per_game         DECIMAL(5,2) DEFAULT 0 COMMENT '场均盖帽',
    -- 风格数据
    fast_break_points       DECIMAL(5,2) COMMENT '快攻得分',
    points_in_paint         DECIMAL(5,2) COMMENT '内线得分',
    second_chance_points    DECIMAL(5,2) COMMENT '二次进攻得分',
    bench_points            DECIMAL(5,2) COMMENT '替补得分',
    -- 稳定性
    points_std              DECIMAL(5,2) COMMENT '得分标准差',
    points_cv               DECIMAL(5,3) COMMENT '得分变异系数',
    create_time             DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time             DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_team_season (team_id, season),
    KEY idx_season (season)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球队赛季数据表';

-- ============================================================
-- 5. 比赛记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS game_record (
    game_id         BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '比赛ID',
    nba_game_id     VARCHAR(30) NOT NULL COMMENT 'NBA官方比赛ID',
    season          VARCHAR(10) NOT NULL COMMENT '赛季',
    game_date       DATE NOT NULL COMMENT '比赛日期',
    game_type       VARCHAR(20) NOT NULL COMMENT '比赛类型(常规赛/季后赛/总决赛)',
    home_team_id    BIGINT NOT NULL COMMENT '主队ID',
    away_team_id    BIGINT NOT NULL COMMENT '客队ID',
    home_score      INT NOT NULL COMMENT '主队得分',
    away_score      INT NOT NULL COMMENT '客队得分',
    home_q1_score   INT COMMENT '主队第一节得分',
    home_q2_score   INT COMMENT '主队第二节得分',
    home_q3_score   INT COMMENT '主队第三节得分',
    home_q4_score   INT COMMENT '主队第四节得分',
    away_q1_score   INT COMMENT '客队第一节得分',
    away_q2_score   INT COMMENT '客队第二节得分',
    away_q3_score   INT COMMENT '客队第三节得分',
    away_q4_score   INT COMMENT '客队第四节得分',
    overtime        TINYINT DEFAULT 0 COMMENT '是否加时(0/1)',
    home_win        TINYINT NOT NULL COMMENT '主队是否获胜(0/1)',
    score_diff      INT NOT NULL COMMENT '分差(主队-客队)',
    total_score     INT NOT NULL COMMENT '总分',
    is_playoff      TINYINT DEFAULT 0 COMMENT '是否季后赛(0/1)',
    playoff_round   VARCHAR(20) COMMENT '季后赛轮次',
    series_id       BIGINT COMMENT '系列赛ID',
    status          VARCHAR(20) DEFAULT 'FINISHED' COMMENT '状态( scheduled/finished )',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_nba_game_id (nba_game_id),
    KEY idx_game_date (game_date),
    KEY idx_season (season),
    KEY idx_home_team (home_team_id),
    KEY idx_away_team (away_team_id),
    KEY idx_series (series_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='比赛记录表';

-- ============================================================
-- 6. 球队对位战绩表
-- ============================================================
CREATE TABLE IF NOT EXISTS battle_record (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    team1_id        BIGINT NOT NULL COMMENT '球队1 ID',
    team2_id        BIGINT NOT NULL COMMENT '球队2 ID',
    season          VARCHAR(10) NOT NULL COMMENT '赛季',
    total_games     INT DEFAULT 0 COMMENT '总交手次数',
    team1_wins      INT DEFAULT 0 COMMENT '球队1胜场',
    team2_wins      INT DEFAULT 0 COMMENT '球队2胜场',
    team1_avg_score DECIMAL(5,2) COMMENT '球队1场均得分',
    team2_avg_score DECIMAL(5,2) COMMENT '球队2场均得分',
    avg_score_diff  DECIMAL(5,2) COMMENT '平均分差',
    team1_home_wins INT DEFAULT 0 COMMENT '球队1主场胜场',
    team1_away_wins INT DEFAULT 0 COMMENT '球队1客场胜场',
    last_game_date  DATE COMMENT '最近交手日期',
    last_game_score VARCHAR(20) COMMENT '最近交手比分',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_team_season (team1_id, team2_id, season),
    KEY idx_team1 (team1_id),
    KEY idx_team2 (team2_id),
    KEY idx_season (season)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='球队对位战绩表';

-- ============================================================
-- 7. 赔率数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS odds_data (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    game_id         BIGINT COMMENT '比赛ID',
    game_date       DATE NOT NULL COMMENT '比赛日期',
    home_team_id    BIGINT NOT NULL COMMENT '主队ID',
    away_team_id    BIGINT NOT NULL COMMENT '客队ID',
    source_id       BIGINT NOT NULL COMMENT '数据源ID',
    -- 胜负赔率
    home_win_odds   DECIMAL(8,3) COMMENT '主胜赔率(欧赔)',
    away_win_odds   DECIMAL(8,3) COMMENT '客胜赔率(欧赔)',
    home_win_prob   DECIMAL(5,3) COMMENT '主胜概率',
    away_win_prob   DECIMAL(5,3) COMMENT '客胜概率',
    -- 让分盘
    handicap_line   DECIMAL(5,1) COMMENT '让分盘口(主队让分)',
    handicap_home_odds DECIMAL(8,3) COMMENT '让分主胜赔率',
    handicap_away_odds DECIMAL(8,3) COMMENT '让分客胜赔率',
    -- 大小分盘
    total_line      DECIMAL(5,1) COMMENT '大小分盘口',
    over_odds       DECIMAL(8,3) COMMENT '大分赔率',
    under_odds      DECIMAL(8,3) COMMENT '小分赔率',
    -- 换算系数
    home_win_coeff  DECIMAL(5,3) COMMENT '主胜修正系数',
    away_win_coeff  DECIMAL(5,3) COMMENT '客胜修正系数',
    total_coeff     DECIMAL(5,3) COMMENT '总分修正系数',
    diff_coeff      DECIMAL(5,3) COMMENT '分差修正系数',
    -- 数据质量
    data_quality    VARCHAR(20) DEFAULT 'NORMAL' COMMENT '数据质量(NORMAL/ABNORMAL/MISSING)',
    collect_time    DATETIME COMMENT '采集时间',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_game_source (game_id, source_id),
    KEY idx_game_date (game_date),
    KEY idx_source (source_id),
    KEY idx_home_team (home_team_id),
    KEY idx_away_team (away_team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赔率数据表';

-- ============================================================
-- 8. 赔率数据源配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS odds_source (
    source_id       BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '数据源ID',
    source_name     VARCHAR(50) NOT NULL COMMENT '数据源名称',
    source_code     VARCHAR(20) NOT NULL COMMENT '数据源代码(win007/covers/okooo/oddsportal)',
    source_url      VARCHAR(200) COMMENT '数据源URL',
    source_type     VARCHAR(20) NOT NULL COMMENT '采集方式(API/CRAWLER)',
    -- 评分指标
    mae_score       DECIMAL(5,2) COMMENT 'MAE得分(满分100)',
    calibration_score DECIMAL(5,2) COMMENT '市场校准度得分',
    completeness_score DECIMAL(5,2) COMMENT '数据完整性得分',
    timeliness_score DECIMAL(5,2) COMMENT '更新及时性得分',
    stability_score DECIMAL(5,2) COMMENT '稳定性得分',
    total_score     DECIMAL(5,2) COMMENT '综合评分',
    -- 状态
    priority        INT DEFAULT 0 COMMENT '优先级(0-最高)',
    is_primary      TINYINT DEFAULT 0 COMMENT '是否主数据源(0/1)',
    status          VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态(ACTIVE/INACTIVE/ERROR)',
    last_collect_time DATETIME COMMENT '最近采集时间',
    last_error      VARCHAR(500) COMMENT '最近错误信息',
    error_count     INT DEFAULT 0 COMMENT '连续错误次数',
    -- 配置
    collect_interval INT DEFAULT 30 COMMENT '采集间隔(分钟)',
    retry_count     INT DEFAULT 3 COMMENT '重试次数',
    timeout         INT DEFAULT 10 COMMENT '超时时间(秒)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_source_code (source_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赔率数据源配置表';

-- ============================================================
-- 9. 预测记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS predict_record (
    predict_id      BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '预测ID',
    predict_type    VARCHAR(20) NOT NULL COMMENT '预测类型(PLAYER/TEAM)',
    game_id         BIGINT COMMENT '比赛ID',
    game_date       DATE COMMENT '比赛日期',
    -- 球员预测相关
    player_id       BIGINT COMMENT '球员ID',
    opponent_player_id BIGINT COMMENT '对位球员ID',
    -- 球队预测相关
    home_team_id    BIGINT COMMENT '主队ID',
    away_team_id    BIGINT COMMENT '客队ID',
    -- 预测参数
    scene           VARCHAR(20) COMMENT '比赛场景(常规赛/季后赛/关键战)',
    use_odds        TINYINT DEFAULT 0 COMMENT '是否使用赔率融合(0/1)',
    odds_source_id  BIGINT COMMENT '赔率数据源ID',
    -- 球员预测结果
    predict_points_low  DECIMAL(5,2) COMMENT '预测得分-拉胯区间',
    predict_points_mid  DECIMAL(5,2) COMMENT '预测得分-常规区间',
    predict_points_high DECIMAL(5,2) COMMENT '预测得分-爆发区间',
    predict_fg_pct      DECIMAL(5,3) COMMENT '预测命中率',
    -- 球队预测结果(纯系统)
    predict_home_score  INT COMMENT '预测主队得分(系统)',
    predict_away_score  INT COMMENT '预测客队得分(系统)',
    predict_total_score INT COMMENT '预测总分(系统)',
    predict_score_diff  INT COMMENT '预测分差(系统)',
    -- 球队预测结果(融合)
    predict_home_score_odds INT COMMENT '预测主队得分(融合)',
    predict_away_score_odds INT COMMENT '预测客队得分(融合)',
    predict_total_score_odds INT COMMENT '预测总分(融合)',
    predict_score_diff_odds INT COMMENT '预测分差(融合)',
    -- 系数记录
    all_star_coeff      DECIMAL(5,3) COMMENT '全明星系数',
    veteran_coeff       DECIMAL(5,3) COMMENT '老将系数',
    injury_coeff        DECIMAL(5,3) COMMENT '伤病系数',
    clutch_coeff        DECIMAL(5,3) COMMENT '关键球系数',
    home_coeff          DECIMAL(5,3) COMMENT '主场系数',
    fatigue_coeff       DECIMAL(5,3) COMMENT '疲劳系数',
    odds_coeff          DECIMAL(5,3) COMMENT '赔率修正系数',
    total_coeff         DECIMAL(5,3) COMMENT '总修正系数',
    -- 真实结果(比赛结束后回填)
    real_points         INT COMMENT '真实得分(球员)',
    real_fg_pct         DECIMAL(5,3) COMMENT '真实命中率',
    real_home_score     INT COMMENT '真实主队得分',
    real_away_score     INT COMMENT '真实客队得分',
    real_total_score    INT COMMENT '真实总分',
    real_score_diff     INT COMMENT '真实分差',
    -- 误差
    error_points        DECIMAL(5,2) COMMENT '得分误差',
    error_total         INT COMMENT '总分误差',
    error_diff          INT COMMENT '分差误差',
    -- 状态
    status              VARCHAR(20) DEFAULT 'PENDING' COMMENT '状态(PENDING/FINISHED/CALIBRATED)',
    create_time         DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    KEY idx_predict_type (predict_type),
    KEY idx_game_date (game_date),
    KEY idx_player (player_id),
    KEY idx_home_team (home_team_id),
    KEY idx_away_team (away_team_id),
    KEY idx_status (status),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测记录表';

-- ============================================================
-- 10. 系列赛之星表
-- ============================================================
CREATE TABLE IF NOT EXISTS series_star (
    star_id         BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '之星ID',
    series_id       BIGINT NOT NULL COMMENT '系列赛ID',
    player_id       BIGINT NOT NULL COMMENT '球员ID',
    team_id         BIGINT NOT NULL COMMENT '球队ID',
    opponent_team_id BIGINT NOT NULL COMMENT '对手球队ID',
    season          VARCHAR(10) NOT NULL COMMENT '赛季',
    -- 数据提升
    avg_score       DECIMAL(5,2) COMMENT '系列赛场均得分',
    avg_fg_pct      DECIMAL(5,3) COMMENT '系列赛命中率',
    score_up        DECIMAL(5,2) COMMENT '得分提升幅度',
    hit_rate_up     DECIMAL(5,3) COMMENT '命中率提升幅度',
    -- 判定
    judge_threshold_score DECIMAL(5,2) DEFAULT 5.0 COMMENT '得分提升阈值',
    judge_threshold_pct   DECIMAL(5,3) DEFAULT 0.10 COMMENT '命中率提升阈值',
    is_star         TINYINT DEFAULT 0 COMMENT '是否为系列赛之星(0/1)',
    -- 关键场次
    key_game_id     BIGINT COMMENT '关键场次比赛ID',
    key_game_score  INT COMMENT '关键场次得分',
    key_game_fg_pct DECIMAL(5,3) COMMENT '关键场次命中率',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_series_player (series_id, player_id),
    KEY idx_player (player_id),
    KEY idx_team (team_id),
    KEY idx_season (season),
    KEY idx_is_star (is_star)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系列赛之星表';

-- ============================================================
-- 11. 箭头人物对位数据表(后台)
-- ============================================================
CREATE TABLE IF NOT EXISTS player_matchup (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    game_id         BIGINT NOT NULL COMMENT '比赛ID',
    game_date       DATE NOT NULL COMMENT '比赛日期',
    season          VARCHAR(10) NOT NULL COMMENT '赛季',
    -- 进攻球员
    offense_player_id BIGINT NOT NULL COMMENT '进攻球员ID',
    offense_team_id   BIGINT NOT NULL COMMENT '进攻球员球队ID',
    offense_rank      INT COMMENT '队内得分排名',
    -- 防守球员
    defense_player_id BIGINT NOT NULL COMMENT '防守球员ID',
    defense_team_id   BIGINT NOT NULL COMMENT '防守球员球队ID',
    -- 对位数据
    position_diff     VARCHAR(10) COMMENT '位置差异',
    matchup_minutes   INT COMMENT '对位时间(秒)',
    offense_points    INT COMMENT '对位时得分',
    offense_attempts  INT COMMENT '对位时出手',
    offense_made      INT COMMENT '对位时命中',
    offense_efficiency DECIMAL(5,2) COMMENT '对位进攻效率',
    defense_efficiency DECIMAL(5,2) COMMENT '对位防守效率',
    net_efficiency    DECIMAL(5,2) COMMENT '净效率',
    -- 综合评分
    per_score         DECIMAL(5,2) COMMENT 'PER评分',
    ts_score          DECIMAL(5,3) COMMENT '真实命中率评分',
    usage_score       DECIMAL(5,3) COMMENT '回合占有率评分',
    composite_score   DECIMAL(5,2) COMMENT '综合评分',
    create_time       DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    KEY idx_game (game_id),
    KEY idx_game_date (game_date),
    KEY idx_offense_player (offense_player_id),
    KEY idx_defense_player (defense_player_id),
    KEY idx_season (season)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='箭头人物对位数据表';

-- ============================================================
-- 12. 系统配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_id       BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    config_group    VARCHAR(50) NOT NULL COMMENT '配置分组(COEFFICIENT/OPTIMIZATION/DATASOURCE/SYSTEM)',
    config_key      VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value    VARCHAR(500) NOT NULL COMMENT '配置值',
    config_type     VARCHAR(20) DEFAULT 'STRING' COMMENT '值类型(STRING/NUMBER/BOOLEAN/JSON)',
    description     VARCHAR(200) COMMENT '配置说明',
    min_value       DECIMAL(10,4) COMMENT '最小值(数值类型)',
    max_value       DECIMAL(10,4) COMMENT '最大值(数值类型)',
    default_value   VARCHAR(500) COMMENT '默认值',
    is_system       TINYINT DEFAULT 0 COMMENT '是否系统配置(不可删除)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_group_key (config_group, config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ============================================================
-- 13. 定时任务日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS schedule_task_log (
    log_id          BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    task_name       VARCHAR(100) NOT NULL COMMENT '任务名称',
    task_group      VARCHAR(50) COMMENT '任务分组',
    execute_time    DATETIME NOT NULL COMMENT '执行时间',
    finish_time     DATETIME COMMENT '完成时间',
    duration        INT COMMENT '执行时长(秒)',
    execute_status  VARCHAR(20) NOT NULL COMMENT '执行状态(SUCCESS/FAIL/RUNNING)',
    result          TEXT COMMENT '执行结果',
    error_msg       TEXT COMMENT '错误信息',
    retry_count     INT DEFAULT 0 COMMENT '重试次数',
    max_retry       INT DEFAULT 1 COMMENT '最大重试次数',
    trigger_type    VARCHAR(20) COMMENT '触发类型(SCHEDULED/MANUAL)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_task_name (task_name),
    KEY idx_execute_time (execute_time),
    KEY idx_status (execute_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务日志表';

-- ============================================================
-- 14. 算法参数快照表
-- ============================================================
CREATE TABLE IF NOT EXISTS algorithm_param_snapshot (
    snapshot_id     BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '快照ID',
    version         VARCHAR(20) NOT NULL COMMENT '版本号',
    param_json      JSON NOT NULL COMMENT '参数JSON',
    description     VARCHAR(200) COMMENT '快照说明',
    mae_score       DECIMAL(5,2) COMMENT '该版本MAE评分',
    is_current      TINYINT DEFAULT 0 COMMENT '是否当前版本(0/1)',
    create_time     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_version (version),
    KEY idx_is_current (is_current)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='算法参数快照表';

-- ============================================================
-- 初始化数据
-- ============================================================

-- 初始化赔率数据源
INSERT INTO odds_source (source_name, source_code, source_url, source_type, priority, is_primary, status) VALUES
('球探网', 'win007', 'https://basketball.win007.com', 'CRAWLER', 1, 1, 'ACTIVE'),
('Covers', 'covers', 'https://www.covers.com', 'CRAWLER', 2, 0, 'ACTIVE'),
('澳客网', 'okooo', 'https://www.okooo.com', 'CRAWLER', 3, 0, 'ACTIVE'),
('OddsPortal', 'oddsportal', 'https://www.oddsportal.com', 'CRAWLER', 4, 0, 'ACTIVE');

-- 初始化系统配置(系数初始值 - 取范围中值)
INSERT INTO system_config (config_group, config_key, config_value, config_type, description, min_value, max_value, default_value, is_system) VALUES
-- 系数配置
('COEFFICIENT', 'all_star_coeff', '1.200', 'NUMBER', '全明星系数', 1.000, 1.400, '1.200', 1),
('COEFFICIENT', 'veteran_coeff', '0.875', 'NUMBER', '老将系数', 0.800, 0.950, '0.875', 1),
('COEFFICIENT', 'injury_coeff', '0.850', 'NUMBER', '伤病系数', 0.700, 1.000, '0.850', 1),
('COEFFICIENT', 'clutch_coeff', '1.000', 'NUMBER', '关键球系数', 0.700, 1.300, '1.000', 1),
('COEFFICIENT', 'home_coeff', '1.055', 'NUMBER', '主场系数', 1.030, 1.080, '1.055', 1),
('COEFFICIENT', 'fatigue_coeff', '0.960', 'NUMBER', '疲劳系数', 0.920, 1.000, '0.960', 1),
('COEFFICIENT', 'odds_weight', '0.200', 'NUMBER', '赔率融合权重', 0.000, 0.300, '0.200', 1),
('COEFFICIENT', 'stability_coeff', '0.950', 'NUMBER', '稳定性系数', 0.850, 1.050, '0.950', 1),
-- 优化配置
('OPTIMIZATION', 'learning_rate', '0.005', 'NUMBER', '学习率', 0.001, 0.010, '0.005', 1),
('OPTIMIZATION', 'optimization_enabled', 'true', 'BOOLEAN', '是否启用自动优化', NULL, NULL, 'true', 1),
('OPTIMIZATION', 'min_games_for_optimization', '30', 'NUMBER', '最少比赛数才触发优化', 10, 100, '30', 1),
-- 数据源配置
('DATASOURCE', 'auto_switch_enabled', 'true', 'BOOLEAN', '是否启用自动切换', NULL, NULL, 'true', 1),
('DATASOURCE', 'collect_interval_minutes', '30', 'NUMBER', '采集间隔(分钟)', 5, 120, '30', 1),
('DATASOURCE', 'max_error_count', '5', 'NUMBER', '最大连续错误次数', 1, 20, '5', 1),
-- 系统配置
('SYSTEM', 'predict_cache_minutes', '5', 'NUMBER', '预测缓存时间(分钟)', 1, 60, '5', 1),
('SYSTEM', 'odds_fusion_enabled', 'true', 'BOOLEAN', '是否启用赔率融合', NULL, NULL, 'true', 1),
('SYSTEM', 'series_star_score_threshold', '5.0', 'NUMBER', '系列赛之星得分阈值', 3.0, 10.0, '5.0', 1),
('SYSTEM', 'series_star_pct_threshold', '0.10', 'NUMBER', '系列赛之星命中率阈值', 0.05, 0.20, '0.10', 1),
('SYSTEM', 'arrow_player_top_n', '2', 'NUMBER', '箭头人物取前N名', 1, 3, '2', 1);

-- 初始化NBA 30支球队
INSERT INTO team (nba_id, team_name, team_name_en, abbreviation, conference, division) VALUES
-- 东部联盟
('1610612737', '老鹰', 'Hawks', 'ATL', 'East', 'Southeast'),
('1610612738', '凯尔特人', 'Celtics', 'BOS', 'East', 'Atlantic'),
('1610612751', '篮网', 'Nets', 'BKN', 'East', 'Atlantic'),
('1610612766', '黄蜂', 'Hornets', 'CHA', 'East', 'Southeast'),
('1610612741', '公牛', 'Bulls', 'CHI', 'East', 'Central'),
('1610612739', '骑士', 'Cavaliers', 'CLE', 'East', 'Central'),
('1610612765', '活塞', 'Pistons', 'DET', 'East', 'Central'),
('1610612754', '步行者', 'Pacers', 'IND', 'East', 'Central'),
('1610612748', '热火', 'Heat', 'MIA', 'East', 'Southeast'),
('1610612749', '雄鹿', 'Bucks', 'MIL', 'East', 'Central'),
('1610612752', '尼克斯', 'Knicks', 'NYK', 'East', 'Atlantic'),
('1610612753', '魔术', 'Magic', 'ORL', 'East', 'Southeast'),
('1610612755', '76人', '76ers', 'PHI', 'East', 'Atlantic'),
('1610612761', '猛龙', 'Raptors', 'TOR', 'East', 'Atlantic'),
('1610612764', '奇才', 'Wizards', 'WAS', 'East', 'Southeast'),
-- 西部联盟
('1610612742', '独行侠', 'Mavericks', 'DAL', 'West', 'Southwest'),
('1610612743', '掘金', 'Nuggets', 'DEN', 'West', 'Northwest'),
('1610612744', '勇士', 'Warriors', 'GSW', 'West', 'Pacific'),
('1610612745', '火箭', 'Rockets', 'HOU', 'West', 'Southwest'),
('1610612746', '快船', 'Clippers', 'LAC', 'West', 'Pacific'),
('1610612747', '湖人', 'Lakers', 'LAL', 'West', 'Pacific'),
('1610612763', '灰熊', 'Grizzlies', 'MEM', 'West', 'Southwest'),
('1610612750', '森林狼', 'Timberwolves', 'MIN', 'West', 'Northwest'),
('1610612740', '鹈鹕', 'Pelicans', 'NOP', 'West', 'Southwest'),
('1610612760', '雷霆', 'Thunder', 'OKC', 'West', 'Northwest'),
('1610612756', '太阳', 'Suns', 'PHX', 'West', 'Pacific'),
('1610612757', '开拓者', 'Trail Blazers', 'POR', 'West', 'Northwest'),
('1610612758', '国王', 'Kings', 'SAC', 'West', 'Pacific'),
('1610612759', '马刺', 'Spurs', 'SAS', 'West', 'Southwest'),
('1610612762', '爵士', 'Jazz', 'UTA', 'West', 'Northwest');
