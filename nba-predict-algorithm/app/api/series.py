"""
系列赛算法接口
"""
from fastapi import APIRouter
from loguru import logger
from typing import List

from app.models.schemas import SeriesStarResponse
from app.services.series_service import SeriesService

router = APIRouter()
series_service = SeriesService()


@router.get("/star", response_model=List[SeriesStarResponse], summary="系列赛之星识别")
async def identify_series_stars(season: str = "2025-26", team_id: int = None):
    """
    识别系列赛之星

    - **season**: 赛季
    - **team_id**: 球队ID(可选)
    """
    logger.info(f"系列赛之星识别请求: season={season}, team_id={team_id}")
    result = series_service.identify_stars(season, team_id)
    return result


@router.get("/review", summary="全赛季复盘")
async def get_series_review(season: str = "2025-26", team_id: int = None):
    """
    获取全赛季系列赛复盘数据

    - **season**: 赛季
    - **team_id**: 球队ID(可选)
    """
    result = series_service.get_review(season, team_id)
    return result
