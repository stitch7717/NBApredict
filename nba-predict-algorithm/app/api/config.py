"""
配置管理接口
"""
from fastapi import APIRouter
from loguru import logger
from typing import List

from app.models.schemas import ConfigResponse, ConfigUpdateRequest
from app.services.config_service import ConfigService

router = APIRouter()
config_service = ConfigService()


@router.get("/get", response_model=List[ConfigResponse], summary="获取配置")
async def get_config(config_group: str = None):
    """
    获取系统配置

    - **config_group**: 配置分组(可选)
    """
    result = config_service.get_config(config_group)
    return result


@router.post("/update", summary="更新配置")
async def update_config(request: ConfigUpdateRequest):
    """
    更新系统配置

    - **config_group**: 配置分组
    - **config_key**: 配置键
    - **config_value**: 配置值
    """
    logger.info(f"配置更新请求: {request.config_group}.{request.config_key}={request.config_value}")
    result = config_service.update_config(request)
    return result


@router.get("/snapshot", summary="获取参数快照")
async def get_snapshots(limit: int = 10):
    """
    获取算法参数快照列表

    - **limit**: 返回数量
    """
    result = config_service.get_snapshots(limit)
    return result


@router.post("/snapshot/rollback/{snapshot_id}", summary="回滚参数")
async def rollback_snapshot(snapshot_id: int):
    """
    回滚到指定参数快照

    - **snapshot_id**: 快照ID
    """
    logger.info(f"参数回滚请求: snapshot_id={snapshot_id}")
    result = config_service.rollback_snapshot(snapshot_id)
    return result
