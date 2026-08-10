"""
配置服务 - 数据库同步版
"""
from loguru import logger
from typing import Optional, List

from app.models.schemas import ConfigResponse, ConfigUpdateRequest
from app.db.config_dao import ConfigDAO
from config.settings import COEFFICIENT_CONFIG


class ConfigService:

    def __init__(self):
        self.config_dao = ConfigDAO()

    def get_config(self, config_group: Optional[str] = None) -> List[dict]:
        from app.db.database import SessionLocal
        from app.db.models import SystemConfig

        with SessionLocal() as db:
            query = db.query(SystemConfig)
            if config_group:
                query = query.filter(SystemConfig.config_group == config_group)
            configs = query.all()

        return [
            {
                "config_id": c.config_id,
                "config_group": c.config_group,
                "config_key": c.config_key,
                "config_value": c.config_value,
                "config_type": c.config_type,
                "description": c.description,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "default_value": c.default_value,
            }
            for c in configs
        ]

    def update_config(self, request: ConfigUpdateRequest) -> dict:
        if request.config_group == "COEFFICIENT":
            coeff_config = COEFFICIENT_CONFIG.get(request.config_key)
            if coeff_config:
                try:
                    value = float(request.config_value)
                    if value < coeff_config["min"] or value > coeff_config["max"]:
                        return {
                            "status": "error",
                            "message": f"值超出范围: [{coeff_config['min']}, {coeff_config['max']}]",
                        }
                except ValueError:
                    return {"status": "error", "message": "无效的数值"}

        self.config_dao.update_config(
            request.config_group, request.config_key, request.config_value
        )

        return {
            "status": "success",
            "message": f"配置已更新: {request.config_group}.{request.config_key}={request.config_value}",
        }

    def get_snapshots(self, limit: int = 10) -> List[dict]:
        from app.db.database import SessionLocal
        from app.db.models import AlgorithmParamSnapshot

        with SessionLocal() as db:
            snapshots = db.query(AlgorithmParamSnapshot).order_by(
                AlgorithmParamSnapshot.create_time.desc()
            ).limit(limit).all()

        return [
            {
                "snapshot_id": s.snapshot_id,
                "version": s.version,
                "description": s.description,
                "params": s.param_json,
                "mae_score": s.mae_score,
                "is_current": bool(s.is_current),
                "create_time": str(s.create_time) if s.create_time else None,
            }
            for s in snapshots
        ]

    def rollback_snapshot(self, snapshot_id: int) -> dict:
        from app.db.database import SessionLocal
        from app.db.models import AlgorithmParamSnapshot

        with SessionLocal() as db:
            snapshot = db.query(AlgorithmParamSnapshot).filter(
                AlgorithmParamSnapshot.snapshot_id == snapshot_id
            ).first()

            if not snapshot or not snapshot.param_json:
                return {"status": "error", "message": f"快照不存在: {snapshot_id}"}

            params = snapshot.param_json if isinstance(snapshot.param_json, dict) else {}

        for key, value in params.items():
            self.config_dao.update_config("COEFFICIENT", key, str(value))

        return {
            "status": "success",
            "message": f"已回滚到快照: {snapshot.description or snapshot.version}",
            "restored_params": params,
        }
