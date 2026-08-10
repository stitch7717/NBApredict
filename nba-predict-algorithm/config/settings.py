"""
NBA预测系统 - 算法层配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "nba_predict")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# FastAPI配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# 缓存配置
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", 5))

# 日志配置
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ERROR_DATA_DIR = DATA_DIR / "error_data"
ERROR_DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR = DATA_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# 系数初始值配置 (范围中值)
COEFFICIENT_CONFIG = {
    "all_star_coeff": {"value": 1.200, "min": 1.000, "max": 1.400, "desc": "全明星系数"},
    "veteran_coeff": {"value": 0.875, "min": 0.800, "max": 0.950, "desc": "老将系数"},
    "injury_coeff": {"value": 0.850, "min": 0.700, "max": 1.000, "desc": "伤病系数"},
    "clutch_coeff": {"value": 1.000, "min": 0.700, "max": 1.300, "desc": "关键球系数"},
    "home_coeff": {"value": 1.055, "min": 1.030, "max": 1.080, "desc": "主场系数"},
    "fatigue_coeff": {"value": 0.960, "min": 0.920, "max": 1.000, "desc": "疲劳系数"},
    "stability_coeff": {"value": 0.950, "min": 0.850, "max": 1.050, "desc": "稳定性系数"},
    "odds_weight": {"value": 0.200, "min": 0.000, "max": 0.300, "desc": "赔率融合权重"},
}

# 优化配置
OPTIMIZATION_CONFIG = {
    "learning_rate": 0.005,
    "min_games_for_optimization": 30,
    "optimization_enabled": True,
}

# 箭头人物配置
ARROW_PLAYER_CONFIG = {
    "top_n": 2,
    "weights": {
        "per": 0.30,
        "true_shooting": 0.25,
        "usage_rate": 0.20,
        "points": 0.25,
    }
}

# 系列赛之星配置
SERIES_STAR_CONFIG = {
    "score_threshold": 5.0,
    "pct_threshold": 0.10,
}

# 聚类配置
CLUSTERING_CONFIG = {
    "player_clusters": 7,
    "team_defense_clusters": 3,
    "team_offense_clusters": 4,
    "random_state": 42,
}

# 数据清洗配置
CLEANING_CONFIG = {
    "garbage_time_diff": 15,
    "garbage_time_minutes": 5,
    "min_minutes_per_game": 15,
    "min_matchup_games": 15,
    "injury_return_games": 3,
}

# 赔率数据源配置
ODDS_SOURCE_CONFIG = {
    "primary_source": "win007",
    "sources": {
        "win007": {
            "name": "球探网",
            "url": "https://basketball.win007.com",
            "type": "CRAWLER",
            "priority": 1,
        },
        "covers": {
            "name": "Covers",
            "url": "https://www.covers.com",
            "type": "CRAWLER",
            "priority": 2,
        },
        "okooo": {
            "name": "澳客网",
            "url": "https://www.okooo.com",
            "type": "CRAWLER",
            "priority": 3,
        },
        "oddsportal": {
            "name": "OddsPortal",
            "url": "https://www.oddsportal.com",
            "type": "CRAWLER",
            "priority": 4,
        }
    }
}

# NBA Stats API配置
NBA_STATS_CONFIG = {
    "base_url": "https://stats.nba.com/stats",
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nba.com/",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
    },
    "timeout": 30,
}
