"""
赔率服务 - 真实赔率换算与数据源评估
"""
from loguru import logger
from typing import Optional
from datetime import date, datetime

from app.models.schemas import OddsCalculateRequest, OddsCalculateResponse
from app.db.team_dao import TeamDAO
from app.db.config_dao import ConfigDAO
from config.settings import ODDS_SOURCE_CONFIG


class OddsService:

    def __init__(self):
        self.team_dao = TeamDAO()
        self.config_dao = ConfigDAO()

    def calculate(self, request: OddsCalculateRequest) -> OddsCalculateResponse:
        """
        赔率换算:
        1. 欧赔 -> 市场预期胜率 (去掉抽水)
        2. 让分盘 -> 分差修正系数
        3. 大小分盘 -> 总分修正系数
        """
        total_implied = (1 / request.home_win_odds) + (1 / request.away_win_odds)
        home_raw = (1 / request.home_win_odds) / total_implied
        away_raw = (1 / request.away_win_odds) / total_implied

        home_win_prob = round(home_raw, 3)
        away_win_prob = round(away_raw, 3)

        coeffs = self.config_dao.get_coefficients()
        base = coeffs.get("home_coeff", 1.055)

        home_win_coeff = round(base * (0.8 + home_win_prob * 0.4), 3)
        away_win_coeff = round((2 - base) * (0.8 + away_win_prob * 0.4), 3)

        total_coeff = None
        diff_coeff = None

        if request.total_line:
            base_total = 215.0
            total_coeff = round(request.total_line / base_total, 3)

        if request.handicap_line:
            diff_coeff = round(1.0 + (request.handicap_line * 0.012), 3)

        return OddsCalculateResponse(
            home_win_prob=home_win_prob,
            away_win_prob=away_win_prob,
            home_win_coeff=home_win_coeff,
            away_win_coeff=away_win_coeff,
            total_coeff=total_coeff,
            diff_coeff=diff_coeff,
        )

    def evaluate_sources(self) -> dict:
        """
        评估赔率数据源

        评估指标:
        1. MAE得分(40%) - 预测误差
        2. 市场校准度(30%) - 与市场一致性
        3. 数据完整性(15%) - 覆盖率
        4. 更新及时性(10%) - 数据时效
        5. 稳定性(5%) - 数据波动
        """
        from app.db.database import SessionLocal
        from app.db.models import OddsSource

        sources_result = []
        with SessionLocal() as db:
            sources = db.query(OddsSource).filter(OddsSource.status == "ACTIVE").all()

            for src in sources:
                mae = src.mae_score or 75.0
                cal = src.calibration_score or 75.0
                comp = src.completeness_score or 75.0
                time_s = src.timeliness_score or 75.0
                stab = src.stability_score or 75.0

                total = mae * 0.40 + cal * 0.30 + comp * 0.15 + time_s * 0.10 + stab * 0.05

                sources_result.append({
                    "source_id": src.source_id,
                    "code": src.source_code,
                    "name": src.source_name,
                    "mae_score": round(mae, 1),
                    "calibration_score": round(cal, 1),
                    "completeness_score": round(comp, 1),
                    "timeliness_score": round(time_s, 1),
                    "stability_score": round(stab, 1),
                    "total_score": round(total, 1),
                    "is_primary": bool(src.is_primary),
                    "priority": src.priority,
                })

        sources_result.sort(key=lambda x: x["total_score"], reverse=True)
        primary = next((s["code"] for s in sources_result if s["is_primary"]), None)

        return {
            "sources": sources_result,
            "primary_source": primary,
            "evaluation_time": datetime.now().isoformat(),
        }

    def collect(self, source_code: str, game_date: Optional[str] = None) -> dict:
        """
        手动采集赔率数据
        实际采集逻辑需对接外部数据源爬虫，此处提供框架
        """
        logger.info(f"开始采集赔率: source={source_code}, date={game_date}")

        source_config = ODDS_SOURCE_CONFIG["sources"].get(source_code)
        if not source_config:
            return {
                "source": source_code,
                "status": "失败",
                "message": f"未知数据源: {source_code}",
            }

        return {
            "source": source_code,
            "source_name": source_config["name"],
            "date": game_date or str(date.today()),
            "status": "采集完成",
            "collected_count": 0,
            "message": f"数据源 {source_config['name']} 采集接口已就绪，需实现具体爬虫逻辑",
        }

    def fuse_with_system(self, system_diff: int, system_total: int,
                         odds_diff: Optional[float], odds_total: Optional[float],
                         weight: float = 0.20) -> dict:
        """
        赔率融合: 系统预测与赔率预测加权融合
        """
        fused_diff = system_diff
        fused_total = system_total

        if odds_diff is not None:
            fused_diff = round(system_diff * (1 - weight) + odds_diff * weight)
        if odds_total is not None:
            fused_total = round(system_total * (1 - weight) + odds_total * weight)

        return {
            "fused_score_diff": fused_diff,
            "fused_total_score": fused_total,
            "system_score_diff": system_diff,
            "system_total_score": system_total,
            "odds_score_diff": odds_diff,
            "odds_total_score": odds_total,
            "weight": weight,
        }
