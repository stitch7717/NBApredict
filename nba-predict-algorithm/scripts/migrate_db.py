"""
数据库迁移脚本
添加高阶数据列，清除旧假数据
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.db.models import Base


# PlayerData 新增列
PLAYER_DATA_COLUMNS = [
    ("offensive_rating", "FLOAT"),
    ("defensive_rating", "FLOAT"),
    ("net_rating", "FLOAT"),
    ("assist_pct", "FLOAT"),
    ("rebound_pct", "FLOAT"),
    ("steal_pct", "FLOAT"),
    ("block_pct", "FLOAT"),
    ("turnover_pct", "FLOAT"),
    ("effective_fg_pct", "FLOAT"),
]

# TeamData 新增列
TEAM_DATA_COLUMNS = [
    ("net_rating", "FLOAT"),
    ("assist_pct", "FLOAT"),
    ("rebound_pct", "FLOAT"),
    ("effective_fg_pct", "FLOAT"),
    ("true_shooting_pct", "FLOAT"),
]

# Player 新增列 (角色与影响力)
PLAYER_COLUMNS = [
    ("player_role", "VARCHAR(30)"),
    ("impact_score", "FLOAT"),
    ("offensive_impact", "FLOAT"),
    ("defensive_impact", "FLOAT"),
    ("team_dependency", "FLOAT"),
    ("stability_score", "FLOAT"),
    ("connector_score", "FLOAT"),
    ("veteran_score", "FLOAT"),
]


def column_exists(db, table_name: str, column_name: str) -> bool:
    """检查列是否已存在"""
    result = db.execute(text(
        f"SHOW COLUMNS FROM `{table_name}` LIKE '{column_name}'"
    ))
    return result.fetchone() is not None


def add_columns():
    """添加新列"""
    logger.info("添加新列...")

    with SessionLocal() as db:
        for col_name, col_type in PLAYER_DATA_COLUMNS:
            if not column_exists(db, "player_data", col_name):
                db.execute(text(
                    f"ALTER TABLE player_data ADD COLUMN `{col_name}` {col_type} DEFAULT NULL"
                ))
                logger.info(f"  player_data.{col_name} 已添加")
            else:
                logger.info(f"  player_data.{col_name} 已存在，跳过")

        for col_name, col_type in TEAM_DATA_COLUMNS:
            if not column_exists(db, "team_data", col_name):
                db.execute(text(
                    f"ALTER TABLE team_data ADD COLUMN `{col_name}` {col_type} DEFAULT NULL"
                ))
                logger.info(f"  team_data.{col_name} 已添加")
            else:
                logger.info(f"  team_data.{col_name} 已存在，跳过")

        for col_name, col_type in PLAYER_COLUMNS:
            if not column_exists(db, "player", col_name):
                db.execute(text(
                    f"ALTER TABLE player ADD COLUMN `{col_name}` {col_type} DEFAULT NULL"
                ))
                logger.info(f"  player.{col_name} 已添加")
            else:
                logger.info(f"  player.{col_name} 已存在，跳过")

        db.commit()
    logger.info("新列添加完成")


def clear_old_data():
    """清除旧的假数据"""
    logger.info("清除旧数据...")

    with SessionLocal() as db:
        # 统计现有数据
        pd_count = db.execute(text("SELECT COUNT(*) FROM player_data")).scalar()
        td_count = db.execute(text("SELECT COUNT(*) FROM team_data")).scalar()
        gr_count = db.execute(text("SELECT COUNT(*) FROM game_record")).scalar()

        logger.info(f"  player_data: {pd_count} 条")
        logger.info(f"  team_data: {td_count} 条")
        logger.info(f"  game_record: {gr_count} 条")

        # 清除假数据
        db.execute(text("DELETE FROM player_data"))
        db.execute(text("DELETE FROM team_data"))
        db.execute(text("DELETE FROM game_record"))
        db.commit()

        logger.info("  已清除 player_data, team_data, game_record")
    logger.info("旧数据清除完成")


def run():
    logger.info("=" * 50)
    logger.info("数据库迁移开始")
    logger.info("=" * 50)

    # 确保表存在
    Base.metadata.create_all(bind=engine)
    logger.info("表结构已确认")

    add_columns()
    clear_old_data()

    logger.info("=" * 50)
    logger.info("迁移完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
