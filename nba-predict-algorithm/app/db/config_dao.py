"""
配置数据访问
"""
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.db.models import SystemConfig
from app.db.database import SessionLocal


class ConfigDAO:

    def get_session(self) -> Session:
        return SessionLocal()

    def get_config_value(self, config_group: str, config_key: str) -> Optional[str]:
        with self.get_session() as db:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_group == config_group,
                SystemConfig.config_key == config_key
            ).first()
            return config.config_value if config else None

    def get_config_map(self, config_group: str) -> Dict[str, str]:
        with self.get_session() as db:
            configs = db.query(SystemConfig).filter(
                SystemConfig.config_group == config_group
            ).all()
            return {c.config_key: c.config_value for c in configs}

    def get_coefficients(self) -> Dict[str, float]:
        """获取所有系数配置"""
        config_map = self.get_config_map("COEFFICIENT")
        return {k: float(v) for k, v in config_map.items()}

    def update_config(self, config_group: str, config_key: str, config_value: str):
        with self.get_session() as db:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_group == config_group,
                SystemConfig.config_key == config_key
            ).first()
            if config:
                config.config_value = config_value
                db.commit()

    def get_system_config(self, config_key: str) -> Optional[str]:
        return self.get_config_value("SYSTEM", config_key)
