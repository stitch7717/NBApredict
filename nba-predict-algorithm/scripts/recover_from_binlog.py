"""
从 MySQL binlog 解析 DELETE 事件，提取被删除的行数据，恢复到数据库。

binlog 中的列顺序是旧 schema（迁移前），需要映射到当前 schema。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from sqlalchemy import text

# ── binlog 中的列顺序（旧 schema，迁移前）──────────────────
# game_record 和 team_data 的列顺序在迁移中未改变
# player_data 的列顺序因迁移而改变（9列从 vorp 后移到 update_time 后）

GAME_RECORD_BINLOG_COLS = [
    "game_id", "nba_game_id", "season", "game_date", "game_type",
    "home_team_id", "away_team_id", "home_score", "away_score",
    "home_q1_score", "home_q2_score", "home_q3_score", "home_q4_score",
    "away_q1_score", "away_q2_score", "away_q3_score", "away_q4_score",
    "overtime", "home_win", "score_diff", "total_score",
    "is_playoff", "playoff_round", "series_id", "status",
    "create_time", "update_time",
]

# binlog 中 player_data 的旧列顺序（@1 到 @38）
PLAYER_DATA_BINLOG_COLS = [
    "id",                          # @1
    "player_id",                   # @2
    "season",                      # @3
    "team_id",                     # @4
    "games_played",                # @5
    "games_started",               # @6
    "minutes_per_game",            # @7
    "points_per_game",             # @8
    "rebounds_per_game",           # @9
    "assists_per_game",            # @10
    "steals_per_game",             # @11
    "blocks_per_game",             # @12
    "turnovers_per_game",          # @13
    "fg_made_per_game",            # @14
    "fg_attempted_per_game",       # @15
    "fg_percentage",               # @16
    "three_made_per_game",         # @17
    "three_attempted_per_game",    # @18
    "three_percentage",            # @19
    "ft_made_per_game",            # @20
    "ft_attempted_per_game",       # @21
    "ft_percentage",               # @22
    "per",                         # @23
    "true_shooting_pct",           # @24
    "usage_rate",                  # @25
    "win_shares",                  # @26
    "bpm",                         # @27
    "vorp",                        # @28
    "offensive_rating",            # @29  ← 旧位置
    "defensive_rating",            # @30
    "net_rating",                  # @31
    "assist_pct",                  # @32
    "rebound_pct",                 # @33
    "steal_pct",                   # @34
    "block_pct",                   # @35
    "turnover_pct",                # @36
    "effective_fg_pct",            # @37
    "points_cv",                   # @38
    # @39-@44: points_std, vs_*_efficiency (不在 INSERT 中)
]

TEAM_DATA_BINLOG_COLS = [
    "id", "team_id", "season",
    "wins", "losses", "win_percentage",
    "home_wins", "home_losses", "away_wins", "away_losses",
    "points_per_game", "assists_per_game", "rebounds_per_game",
    "offensive_rebounds", "turnovers_per_game",
    "fg_percentage", "three_percentage", "ft_percentage",
    "pace", "offensive_rating",
    "opponent_points", "opponent_fg_percentage", "opponent_three_pct",
    "defensive_rating", "steals_per_game", "blocks_per_game",
    "fast_break_points", "points_in_paint", "second_chance_points", "bench_points",
    "points_std", "points_cv",
    "create_time", "update_time",
]

# 当前表中需要 INSERT 的列（按当前 schema 顺序）
GAME_RECORD_INSERT_COLS = [
    "nba_game_id", "season", "game_date", "game_type",
    "home_team_id", "away_team_id", "home_score", "away_score",
    "home_q1_score", "home_q2_score", "home_q3_score", "home_q4_score",
    "away_q1_score", "away_q2_score", "away_q3_score", "away_q4_score",
    "overtime", "home_win", "score_diff", "total_score",
    "is_playoff", "playoff_round", "series_id", "status",
]

# player_data: 旧数据只有前 28 列有值，9 个新列用 DEFAULT
PLAYER_DATA_INSERT_COLS = [
    "player_id", "season", "team_id",
    "games_played", "games_started", "minutes_per_game",
    "points_per_game", "rebounds_per_game", "assists_per_game",
    "steals_per_game", "blocks_per_game", "turnovers_per_game",
    "fg_made_per_game", "fg_attempted_per_game", "fg_percentage",
    "three_made_per_game", "three_attempted_per_game", "three_percentage",
    "ft_made_per_game", "ft_attempted_per_game", "ft_percentage",
    "per", "true_shooting_pct", "usage_rate",
    "win_shares", "bpm", "vorp",
    "offensive_rating", "defensive_rating", "net_rating",
    "assist_pct", "rebound_pct", "steal_pct", "block_pct", "turnover_pct",
    "effective_fg_pct", "points_cv",
]

TEAM_DATA_INSERT_COLS = [
    "team_id", "season",
    "wins", "losses", "win_percentage",
    "home_wins", "home_losses", "away_wins", "away_losses",
    "points_per_game", "assists_per_game", "rebounds_per_game",
    "offensive_rebounds", "turnovers_per_game",
    "fg_percentage", "three_percentage", "ft_percentage",
    "pace", "offensive_rating",
    "opponent_points", "opponent_fg_percentage", "opponent_three_pct",
    "defensive_rating", "steals_per_game", "blocks_per_game",
    "fast_break_points", "points_in_paint", "second_chance_points", "bench_points",
    "points_std", "points_cv",
]


def parse_binlog_value(val_str):
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


def fix_date(val):
    if val and isinstance(val, str) and ":" in val and val.count(":") == 2:
        parts = val.split(":")
        if len(parts[0]) == 4:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return val


def parse_delete_rows(lines, start_idx, table_name, binlog_cols, insert_cols):
    """解析连续的 DELETE 行，返回 (行字典列表, 结束行号)"""
    rows = []
    i = start_idx
    current_row = {}
    table_ref = f"nba_predict`.`{table_name}"

    while i < len(lines):
        line = lines[i].strip()

        if f"### DELETE FROM `{table_ref}`" in line:
            if current_row:
                rows.append(current_row)
            current_row = {}
            i += 1
            if i < len(lines) and ("WHERE" in lines[i] or "where" in lines[i]):
                i += 1
            continue

        if re.match(r"###\s+@\d+=", line):
            match = re.match(r"###\s+@(\d+)=(.*)", line)
            if match:
                col_idx = int(match.group(1)) - 1
                val = parse_binlog_value(match.group(2))
                if col_idx < len(binlog_cols):
                    col_name = binlog_cols[col_idx]
                    if col_name in insert_cols:
                        if col_name == "game_date":
                            val = fix_date(val)
                        current_row[col_name] = val
            i += 1
            continue

        if current_row:
            rows.append(current_row)
            current_row = {}

        if line.startswith("COMMIT") or line.startswith("### Table_map") or line.startswith("# at "):
            break
        if "### DELETE FROM" in line and table_ref not in line:
            break

        i += 1

    if current_row:
        rows.append(current_row)

    return rows, i


PLAYER_BINLOG_COLS = [
    "player_id", "nba_id", "player_name", "player_name_en", "position",
    "jersey_number", "team_id", "birth_date", "age", "height", "weight",
    "draft_year", "draft_round", "draft_pick", "experience",
    "all_star_count", "all_star_last", "injury_status", "injury_type",
    "injury_date", "player_type", "cluster_id", "cluster_name", "status",
    "create_time", "update_time",
]

PLAYER_INSERT_COLS = [c for c in PLAYER_BINLOG_COLS if c not in ("create_time", "update_time")]


def parse_insert_rows(lines, start_idx, table_name, binlog_cols, insert_cols):
    """解析连续的 INSERT (Write_rows) 行"""
    rows = []
    i = start_idx
    current_row = {}
    table_ref = f"nba_predict`.`{table_name}"

    while i < len(lines):
        line = lines[i].strip()

        if f"### INSERT INTO `{table_ref}`" in line:
            if current_row:
                rows.append(current_row)
            current_row = {}
            i += 1
            if i < len(lines) and ("SET" in lines[i] or "VALUES" in lines[i]):
                i += 1
            continue

        if re.match(r"###\s+@\d+=", line):
            match = re.match(r"###\s+@(\d+)=(.*)", line)
            if match:
                col_idx = int(match.group(1)) - 1
                val = parse_binlog_value(match.group(2))
                if col_idx < len(binlog_cols):
                    col_name = binlog_cols[col_idx]
                    if col_name in insert_cols:
                        current_row[col_name] = val
            i += 1
            continue

        if current_row:
            rows.append(current_row)
            current_row = {}

        if line.startswith("COMMIT") or line.startswith("### Table_map") or line.startswith("# at "):
            break
        if "### INSERT INTO" in line and table_ref not in line:
            break

        i += 1

    if current_row:
        rows.append(current_row)

    return rows, i


def extract_all_deletes(binlog_file):
    with open(binlog_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    logger.info(f"binlog 总行数: {len(lines):,}")

    game_records = []
    player_data_rows = []
    team_data_rows = []
    player_inserts = []
    player_deletes = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if "### DELETE FROM `nba_predict`.`game_record`" in line:
            rows, end = parse_delete_rows(lines, i, "game_record", GAME_RECORD_BINLOG_COLS, set(GAME_RECORD_INSERT_COLS))
            game_records.extend(rows)
            i = end
            continue

        if "### DELETE FROM `nba_predict`.`player_data`" in line:
            rows, end = parse_delete_rows(lines, i, "player_data", PLAYER_DATA_BINLOG_COLS, set(PLAYER_DATA_INSERT_COLS))
            player_data_rows.extend(rows)
            i = end
            continue

        if "### DELETE FROM `nba_predict`.`team_data`" in line:
            rows, end = parse_delete_rows(lines, i, "team_data", TEAM_DATA_BINLOG_COLS, set(TEAM_DATA_INSERT_COLS))
            team_data_rows.extend(rows)
            i = end
            continue

        if "### INSERT INTO `nba_predict`.`player`" in line:
            rows, end = parse_insert_rows(lines, i, "player", PLAYER_BINLOG_COLS, set(PLAYER_INSERT_COLS))
            player_inserts.extend(rows)
            i = end
            continue

        if "### DELETE FROM `nba_predict`.`player`" in line:
            rows, end = parse_delete_rows(lines, i, "player", PLAYER_BINLOG_COLS, set(PLAYER_INSERT_COLS))
            player_deletes.extend(rows)
            i = end
            continue

        i += 1

    logger.info(f"提取到: game_record={len(game_records)}, player_data={len(player_data_rows)}, team_data={len(team_data_rows)}")
    logger.info(f"  player INSERT={len(player_inserts)}, DELETE={len(player_deletes)}")
    return game_records, player_data_rows, team_data_rows, player_inserts, player_deletes


def deduplicate_rows(rows, key_fields):
    seen = {}
    for row in rows:
        key = tuple(row.get(f) for f in key_fields)
        seen[key] = row
    return list(seen.values())


def build_insert_sql(table, columns, rows):
    if not rows:
        return []

    col_list = ", ".join(f"`{c}`" for c in columns)
    sqls = []
    batch_size = 50

    for batch_start in range(0, len(rows), batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        values_parts = []
        params = {}
        for idx, row in enumerate(batch):
            placeholders = []
            for col in columns:
                param_name = f"p{batch_start}_{idx}_{col}"
                val = row.get(col)
                placeholders.append(f":{param_name}")
                params[param_name] = val
            values_parts.append(f"({', '.join(placeholders)})")

        sql = f"INSERT IGNORE INTO `{table}` ({col_list}) VALUES {', '.join(values_parts)}"
        sqls.append((sql, params))

    return sqls


def restore_data(game_records, player_data_rows, team_data_rows, player_inserts, player_deletes):
    game_records = deduplicate_rows(game_records, ["nba_game_id", "season"])
    player_data_rows = deduplicate_rows(player_data_rows, ["player_id", "season"])
    team_data_rows = deduplicate_rows(team_data_rows, ["team_id", "season"])

    # 计算最终 player 集合: INSERT - DELETE
    player_by_id = {}
    for p in player_inserts:
        pid = p.get("player_id")
        if pid:
            player_by_id[pid] = p
    for p in player_deletes:
        pid = p.get("player_id")
        if pid and pid in player_by_id:
            del player_by_id[pid]
    final_players = list(player_by_id.values())

    logger.info(f"去重后: game_record={len(game_records)}, player_data={len(player_data_rows)}, team_data={len(team_data_rows)}")
    logger.info(f"  player: INSERT={len(player_inserts)} - DELETE={len(player_deletes)} = 最终 {len(final_players)}")

    # 检查一个样本确认数据正确
    if game_records:
        sample = game_records[0]
        logger.info(f"  game_record 样本: {sample}")
    if player_data_rows:
        sample = player_data_rows[0]
        logger.info(f"  player_data 样本: {sample}")
    if team_data_rows:
        sample = team_data_rows[0]
        logger.info(f"  team_data 样本: {sample}")

    with SessionLocal() as db:
        # 清理当前的模拟数据
        logger.info("\n清理模拟数据...")
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        db.execute(text("DELETE FROM game_record"))
        db.execute(text("DELETE FROM player_data"))
        db.execute(text("DELETE FROM player"))
        db.execute(text("DELETE FROM team_data"))
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()
        logger.info("  模拟数据已清理")

        # 恢复 team_data
        logger.info("\n恢复 team_data...")
        sqls = build_insert_sql("team_data", TEAM_DATA_INSERT_COLS, team_data_rows)
        for sql, params in sqls:
            db.execute(text(sql), params)
        db.commit()
        cnt = db.execute(text("SELECT COUNT(*) FROM team_data")).scalar()
        logger.info(f"  team_data: {cnt} 行")

        # 恢复 player
        logger.info("恢复 player...")
        sqls = build_insert_sql("player", PLAYER_INSERT_COLS, final_players)
        for sql, params in sqls:
            db.execute(text(sql), params)
        db.commit()
        cnt = db.execute(text("SELECT COUNT(*) FROM player")).scalar()
        logger.info(f"  player: {cnt} 行")

        # 恢复 player_data
        logger.info("恢复 player_data...")
        sqls = build_insert_sql("player_data", PLAYER_DATA_INSERT_COLS, player_data_rows)
        for sql, params in sqls:
            db.execute(text(sql), params)
        db.commit()
        cnt = db.execute(text("SELECT COUNT(*) FROM player_data")).scalar()
        logger.info(f"  player_data: {cnt} 行")

        # 恢复 game_record
        logger.info("恢复 game_record...")
        sqls = build_insert_sql("game_record", GAME_RECORD_INSERT_COLS, game_records)
        for sql, params in sqls:
            db.execute(text(sql), params)
        db.commit()
        cnt = db.execute(text("SELECT COUNT(*) FROM game_record")).scalar()
        logger.info(f"  game_record: {cnt} 行")

        # 验证
        logger.info("\n恢复后数据量:")
        for table in ["player", "player_data", "team_data", "game_record"]:
            result = db.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            logger.info(f"  {table}: {result} 行")

        # 验证球员样本
        logger.info("\n球员样本:")
        samples = db.execute(text("SELECT player_id, player_name, position, team_id, experience FROM player ORDER BY player_id LIMIT 10")).fetchall()
        for s in samples:
            logger.info(f"  {s[0]}: {s[1]} ({s[2]}) team={s[3]} exp={s[4]}")

        # 验证赛季分布
        logger.info("\n赛季分布:")
        for season in ["2022-23", "2023-24", "2024-25", "2025-26"]:
            for table, col in [("player_data", "season"), ("team_data", "season"), ("game_record", "season")]:
                cnt = db.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` = :s"), {"s": season}).scalar()
                if cnt > 0:
                    logger.info(f"  {table} [{season}]: {cnt}")


def run():
    binlog_file = str(Path(__file__).resolve().parent.parent / "data" / "binlog_decoded.txt")

    logger.info("=" * 50)
    logger.info("MySQL binlog 数据恢复开始")
    logger.info("=" * 50)

    game_records, player_data_rows, team_data_rows, player_inserts, player_deletes = extract_all_deletes(binlog_file)

    if not game_records and not player_data_rows and not team_data_rows and not player_inserts:
        logger.error("未从 binlog 提取到任何数据!")
        return

    restore_data(game_records, player_data_rows, team_data_rows, player_inserts, player_deletes)

    logger.info("\n" + "=" * 50)
    logger.info("数据恢复完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
