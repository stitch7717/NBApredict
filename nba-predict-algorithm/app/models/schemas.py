"""
Pydantic模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date


class PlayerPredictRequest(BaseModel):
    """球员预测请求"""
    player_id: int = Field(..., gt=0, description="球员ID")
    opponent_player_id: Optional[int] = Field(None, gt=0, description="对位球员ID")
    scene: str = Field(default="常规赛", pattern="^(常规赛|季后赛)$", description="比赛场景")
    home_away: str = Field(default="home", pattern="^(home|away)$", description="主客场")


class TeamPredictRequest(BaseModel):
    """球队预测请求"""
    home_team_id: int = Field(..., gt=0, description="主队ID")
    away_team_id: int = Field(..., gt=0, description="客队ID")
    scene: str = Field(default="常规赛", pattern="^(常规赛|季后赛)$", description="比赛场景")
    use_odds: bool = Field(default=False, description="是否使用赔率融合")


class OddsCalculateRequest(BaseModel):
    """赔率计算请求"""
    home_win_odds: float = Field(..., gt=1.0, description="主胜赔率(>1.0)")
    away_win_odds: float = Field(..., gt=1.0, description="客胜赔率(>1.0)")
    handicap_line: Optional[float] = Field(None, description="让分盘口")
    total_line: Optional[float] = Field(None, gt=0, description="大小分盘口")


class PlayerPredictResponse(BaseModel):
    """球员预测响应"""
    player_id: int
    player_name: str
    scene: str
    # 预测区间
    points_low: float = Field(..., description="得分-拉胯区间")
    points_mid: float = Field(..., description="得分-常规区间")
    points_high: float = Field(..., description="得分-爆发区间")
    fg_pct: float = Field(..., description="预测命中率")
    # 系数
    all_star_coeff: float
    veteran_coeff: float
    injury_coeff: float
    clutch_coeff: float
    home_coeff: float
    fatigue_coeff: float
    total_coeff: float
    # 克制标签
    matchup_tags: List[str] = Field(default_factory=list)


class TeamPredictResponse(BaseModel):
    """球队预测响应"""
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    scene: str
    # 胜率
    home_win_prob: float = Field(..., description="主队胜率 (0-1)")
    # 纯系统预测
    predict_home_score: int
    predict_away_score: int
    predict_total_score: int
    predict_score_diff: int
    # 融合预测(可选)
    predict_home_score_odds: Optional[int] = None
    predict_away_score_odds: Optional[int] = None
    predict_total_score_odds: Optional[int] = None
    predict_score_diff_odds: Optional[int] = None
    # 系数
    coefficients: dict
    # 克制关系
    style_matchup: str


class OddsCalculateResponse(BaseModel):
    """赔率计算响应"""
    home_win_prob: float
    away_win_prob: float
    home_win_coeff: float
    away_win_coeff: float
    total_coeff: Optional[float] = None
    diff_coeff: Optional[float] = None


class SeriesStarResponse(BaseModel):
    """系列赛之星响应"""
    star_id: int
    player_id: int
    player_name: str
    team_name: str
    avg_score: float
    avg_fg_pct: float
    score_up: float
    hit_rate_up: float
    key_game_score: int


class ConfigResponse(BaseModel):
    """配置响应"""
    config_group: str
    config_key: str
    config_value: str
    description: str


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    config_group: str
    config_key: str
    config_value: str
