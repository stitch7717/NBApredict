"""
球队算法接口
"""
from fastapi import APIRouter
from loguru import logger

from app.models.schemas import TeamPredictRequest, TeamPredictResponse
from app.services.team_service import TeamService
from scripts.compute_player_impact import compute_season

router = APIRouter()
team_service = TeamService()


@router.post("/predict", response_model=TeamPredictResponse, summary="球队对战预测")
async def predict_team(request: TeamPredictRequest):
    """
    预测球队对战结果

    - **home_team_id**: 主队ID
    - **away_team_id**: 客队ID
    - **scene**: 比赛场景(常规赛/季后赛/关键战)
    - **use_odds**: 是否使用赔率融合
    """
    logger.info(f"球队预测请求: home={request.home_team_id}, away={request.away_team_id}")
    result = team_service.predict(request)
    return result


@router.get("/classify", summary="球队聚类分类")
async def classify_teams(season: str = "2025-26"):
    """
    执行球队KMeans聚类分类

    - **season**: 赛季
    """
    logger.info(f"球队聚类请求: season={season}")
    result = team_service.classify(season)
    return result


@router.get("/matchup/{team1_id}/{team2_id}", summary="球队克制关系")
async def get_team_matchup(team1_id: int, team2_id: int):
    """
    获取两队的克制关系分析

    - **team1_id**: 球队1 ID
    - **team2_id**: 球队2 ID
    """
    result = team_service.get_matchup(team1_id, team2_id)
    return result


@router.get("/injury-impact/{team_id}", summary="球队伤病影响分析")
async def get_team_injury_impact(team_id: int):
    """
    分析球队伤病对攻防两端的影响

    - **team_id**: 球队ID
    """
    result = team_service._calc_injury_impact(team_id)
    return {
        "team_id": team_id,
        "off_penalty": result["off_penalty"],
        "def_penalty": result["def_penalty"],
        "chemistry_penalty": result.get("chemistry_penalty", 0),
        "injured_count": len(result["details"]),
        "injured_players": result["details"],
    }


@router.post("/impact/refresh", summary="刷新球员影响力数据")
async def refresh_player_impact(season: str = "2025-26"):
    """
    重新计算所有球员的角色与影响力

    - **season**: 赛季
    """
    logger.info(f"手动刷新球员影响力: {season}")
    try:
        compute_season(season)
        return {"status": "success", "message": f"球员影响力已更新 ({season})"}
    except Exception as e:
        logger.error(f"球员影响力刷新失败: {e}")
        return {"status": "error", "message": str(e)}
