"""
球员算法接口
"""
from fastapi import APIRouter
from loguru import logger
from typing import List

from app.models.schemas import PlayerPredictRequest, PlayerPredictResponse
from app.services.player_service import PlayerService

router = APIRouter()
player_service = PlayerService()


@router.post("/predict", response_model=PlayerPredictResponse, summary="球员表现预测")
async def predict_player(request: PlayerPredictRequest):
    """
    预测球员单场表现

    - **player_id**: 球员ID
    - **opponent_player_id**: 对位球员ID(可选)
    - **scene**: 比赛场景(常规赛/季后赛/关键战)
    - **home_away**: 主客场(home/away)
    """
    logger.info(f"球员预测请求: player_id={request.player_id}, scene={request.scene}")
    result = player_service.predict(request)
    return result


@router.get("/classify", summary="球员聚类分类")
async def classify_players(season: str = "2025-26"):
    """
    执行球员KMeans聚类分类

    - **season**: 赛季
    """
    logger.info(f"球员聚类请求: season={season}")
    result = player_service.classify(season)
    return result


@router.get("/coefficients/{player_id}", summary="获取球员系数")
async def get_player_coefficients(player_id: int, scene: str = "常规赛"):
    """
    获取球员的各项系数

    - **player_id**: 球员ID
    - **scene**: 比赛场景
    """
    result = player_service.get_coefficients(player_id, scene)
    return result


@router.post("/injury/refresh", summary="刷新伤病报告")
async def refresh_injury_report():
    """
    从 ESPN API 获取最新伤病报告并更新到数据库
    """
    logger.info("手动刷新伤病报告")
    try:
        from scripts.fetch_injury_report import run as injury_run
        injury_run()
        return {"status": "success", "message": "伤病报告已更新"}
    except Exception as e:
        logger.error(f"伤病报告刷新失败: {e}")
        return {"status": "error", "message": str(e)}
