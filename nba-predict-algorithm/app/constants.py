"""
NBA预测系统 - 常量定义
"""
from typing import Literal

# 默认赛季
DEFAULT_SEASON = "2025-26"

# 比赛场景
SCENES = ["常规赛", "季后赛", "关键战"]
SceneType = Literal["常规赛", "季后赛", "关键战"]

# 主客场
HOME_AWAY = ["home", "away"]
HomeAwayType = Literal["home", "away"]

# 伤病状态
INJURY_STATUS = {
    "HEALTHY": "健康",
    "RECOVERY": "恢复中",
    "INJURED": "伤病",
}

# 聚类配置
PLAYER_CLUSTER_COUNT = 7
DEFENSE_CLUSTER_COUNT = 3
OFFENSE_CLUSTER_COUNT = 4

# 球队风格
DEFENSE_STYLES = ["防守型", "均衡型", "进攻型"]
OFFENSE_STYLES = ["内线型", "三分型", "快攻型", "阵地型"]

# 球员角色
PLAYER_ROLES = [
    "控球后卫", "得分后卫", "小前锋", "大前锋", "中锋",
    "第六人", "防守专家", "三分射手", "组织核心", "篮板手",
    "盖帽手", "抢断手", "挡拆手", "低位得分手", "侧翼防守者",
]

# 算法端点路径
ALGO_PLAYER_PREDICT = "/algorithm/player/predict"
ALGO_TEAM_PREDICT = "/algorithm/team/predict"
ALGO_ODDS_CONVERT = "/algorithm/odds/convert"
ALGO_SERIES_REVIEW = "/algorithm/series/review"
