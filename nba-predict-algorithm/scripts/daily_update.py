"""
每日数据更新脚本
使用 nba_api 抓取最新数据并更新统计
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord


def needs_update() -> bool:
    """检查是否需要更新"""
    with SessionLocal() as db:
        latest = db.query(GameRecord).order_by(
            GameRecord.game_date.desc()
        ).first()

        if not latest:
            return True

        days_since = (datetime.now().date() - latest.game_date).days
        return days_since >= 1


def run():
    logger.info("=" * 50)
    logger.info(f"每日数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 50)

    if not needs_update():
        logger.info("数据已是最新，跳过更新")
        return

    # Step 1: 使用 nba_api 抓取最新数据
    logger.info("Step 1: 使用 nba_api 抓取最新数据...")
    try:
        from scripts.fetch_nba_data import run as fetch_run
        fetch_run()
    except Exception as e:
        logger.error(f"数据抓取失败: {e}")

    # Step 1.5: 更新伤病报告
    logger.info("Step 1.5: 更新伤病报告...")
    try:
        from scripts.fetch_injury_report import run as injury_run
        injury_run()
    except Exception as e:
        logger.error(f"伤病报告更新失败: {e}")

    # Step 2: 更新球队衍生统计 (主客场拆分、近 10 场等)
    logger.info("Step 2: 更新球队统计...")
    try:
        from scripts.compute_team_stats import compute_season
        current_season = "2025-26"
        compute_season(current_season)
    except Exception as e:
        logger.error(f"更新球队统计失败: {e}")

    # Step 2.5: 计算球员角色与影响力
    logger.info("Step 2.5: 计算球员角色与影响力...")
    try:
        from scripts.compute_player_impact import run as impact_run
        impact_run()
    except Exception as e:
        logger.error(f"球员影响力计算失败: {e}")

    # Step 3: 检查是否需要重新训练模型 (每周一次)
    today = datetime.now()
    if today.weekday() == 0:  # 周一
        logger.info("Step 3: 重新训练模型...")
        try:
            from scripts.train_model import train_and_evaluate
            train_and_evaluate()
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
    else:
        logger.info("Step 3: 跳过模型训练 (每周一执行)")

    logger.info("=" * 50)
    logger.info("更新完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
