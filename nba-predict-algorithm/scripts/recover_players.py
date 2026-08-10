"""
从 binlog 提取与 player_data 匹配的 player 记录
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from sqlalchemy import text

PLAYER_COLS = [
    "player_id", "nba_id", "player_name", "player_name_en", "position",
    "jersey_number", "team_id", "birth_date", "age", "height", "weight",
    "draft_year", "draft_round", "draft_pick", "experience",
    "all_star_count", "all_star_last", "injury_status", "injury_type",
    "injury_date", "player_type", "cluster_id", "cluster_name", "status",
    "create_time", "update_time",
]

INSERT_COLS = [c for c in PLAYER_COLS if c not in ("create_time", "update_time")]


def parse_val(val_str):
    val_str = val_str.strip()
    if val_str == "NULL":
        return None
    if val_str.startswith("'") and val_str.endswith("'"):
        return val_str[1:-1]
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str


def main():
    binlog_file = Path(__file__).resolve().parent.parent / "data" / "binlog_decoded.txt"

    with open(binlog_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # 1. 获取 player_data 中引用的所有 player_id
    with SessionLocal() as db:
        referenced_ids = set()
        rows = db.execute(text("SELECT DISTINCT player_id FROM player_data")).fetchall()
        for r in rows:
            referenced_ids.add(r[0])
    logger.info(f"player_data 引用的 player_id 数量: {len(referenced_ids)}")
    logger.info(f"  范围: {min(referenced_ids)} - {max(referenced_ids)}")

    # 2. 从 binlog 提取所有 player INSERT
    all_players = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '### INSERT INTO `nba_predict`.`player`' in line:
            current = {}
            i += 1
            if i < len(lines) and ("SET" in lines[i] or "VALUES" in lines[i]):
                i += 1
            while i < len(lines):
                l = lines[i].strip()
                if re.match(r"###\s+@\d+=", l):
                    m = re.match(r"###\s+@(\d+)=(.*)", l)
                    if m:
                        idx = int(m.group(1)) - 1
                        val = parse_val(m.group(2))
                        if idx < len(PLAYER_COLS):
                            col = PLAYER_COLS[idx]
                            if col in INSERT_COLS:
                                current[col] = val
                    i += 1
                else:
                    break
            if current and current.get("player_id"):
                all_players.append(current)
            continue
        i += 1

    logger.info(f"binlog 中 player INSERT 总数: {len(all_players)}")

    # 3. 过滤出被 player_data 引用的球员
    matched = [p for p in all_players if p["player_id"] in referenced_ids]
    logger.info(f"匹配的球员数: {len(matched)}")

    # 4. 去重 (保留最后出现的)
    by_id = {}
    for p in matched:
        by_id[p["player_id"]] = p
    final = list(by_id.values())
    logger.info(f"去重后: {len(final)}")

    if final:
        logger.info(f"  样本: {final[0]['player_id']} {final[0]['player_name']} {final[0]['position']}")
        logger.info(f"  样本: {final[-1]['player_id']} {final[-1]['player_name']} {final[-1]['position']}")

    # 5. 写入数据库
    with SessionLocal() as db:
        # 清除当前 player 表
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        db.execute(text("DELETE FROM player"))
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()
        logger.info("已清理 player 表")

        # 批量插入
        col_list = ", ".join(f"`{c}`" for c in INSERT_COLS)
        batch_size = 50
        for batch_start in range(0, len(final), batch_size):
            batch = final[batch_start:batch_start + batch_size]
            values_parts = []
            params = {}
            for idx, row in enumerate(batch):
                placeholders = []
                for col in INSERT_COLS:
                    pname = f"p{batch_start}_{idx}_{col}"
                    placeholders.append(f":{pname}")
                    params[pname] = row.get(col)
                values_parts.append(f"({', '.join(placeholders)})")
            sql = f"INSERT IGNORE INTO `player` ({col_list}) VALUES {', '.join(values_parts)}"
            db.execute(text(sql), params)
        db.commit()

        cnt = db.execute(text("SELECT COUNT(*) FROM player")).scalar()
        logger.info(f"player 表: {cnt} 行")

        # 验证 JOIN
        sample = db.execute(text("""
            SELECT p.player_id, p.player_name, pd.season, pd.points_per_game
            FROM player_data pd
            JOIN player p ON pd.player_id = p.player_id
            WHERE pd.season = '2025-26'
            ORDER BY pd.points_per_game DESC
            LIMIT 5
        """)).fetchall()
        logger.info("\nTop 5 得分 (2025-26):")
        for s in sample:
            logger.info(f"  {s[0]}: {s[1]} - {s[3]} PPG ({s[2]})")


if __name__ == "__main__":
    main()
