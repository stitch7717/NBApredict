"""
赔率算法接口
"""
from fastapi import APIRouter
from loguru import logger

from app.models.schemas import OddsCalculateRequest, OddsCalculateResponse
from app.services.odds_service import OddsService

router = APIRouter()
odds_service = OddsService()


@router.post("/calculate", response_model=OddsCalculateResponse, summary="赔率换算")
async def calculate_odds(request: OddsCalculateRequest):
    """
    将赔率换算为修正系数

    - **home_win_odds**: 主胜赔率(欧赔)
    - **away_win_odds**: 客胜赔率(欧赔)
    - **handicap_line**: 让分盘口(可选)
    - **total_line**: 大小分盘口(可选)
    """
    logger.info(f"赔率换算请求: home_odds={request.home_win_odds}, away_odds={request.away_win_odds}")
    result = odds_service.calculate(request)
    return result


@router.get("/evaluate", summary="数据源评估")
async def evaluate_sources():
    """
    评估各赔率数据源的综合评分
    """
    logger.info("数据源评估请求")
    result = odds_service.evaluate_sources()
    return result


@router.get("/collect/{source_code}", summary="手动采集赔率")
async def collect_odds(source_code: str, game_date: str = None):
    """
    手动触发指定数据源的赔率采集

    - **source_code**: 数据源代码(win007/covers/okooo/oddsportal)
    - **game_date**: 比赛日期(可选，默认今天)
    """
    logger.info(f"手动采集请求: source={source_code}, date={game_date}")
    result = odds_service.collect(source_code, game_date)
    return result
