"""
清理球员数据：去重 + 重新聚合赛季统计
"""
import sys
sys.path.insert(0, ".")

from app.db.database import SessionLocal
from app.db.models import Player, PlayerData
from sqlalchemy import text


def cleanup():
    db = SessionLocal()

    try:
        # 1. 先处理 player_data 中的重复（同一 player_id + season 有多条）
        print("=== Step 1: 合并 player_data 重复条目 ===")
        result = db.execute(text("""
            SELECT player_id, season, COUNT(*) as cnt
            FROM player_data
            GROUP BY player_id, season
            HAVING cnt > 1
        """))
        dup_seasons = [(row[0], row[1], row[2]) for row in result]
        print(f"发现 {len(dup_seasons)} 个重复 player-season 条目")

        for pid, season, cnt in dup_seasons:
            rows = db.execute(text("""
                SELECT id, games_played, minutes_per_game, points_per_game,
                       rebounds_per_game, assists_per_game, steals_per_game,
                       blocks_per_game, turnovers_per_game,
                       fg_made_per_game, fg_attempted_per_game, fg_percentage,
                       three_made_per_game, three_attempted_per_game, three_percentage,
                       ft_made_per_game, ft_attempted_per_game, ft_percentage,
                       true_shooting_pct, effective_fg_pct, usage_rate,
                       assist_pct, rebound_pct, steal_pct, block_pct, turnover_pct
                FROM player_data
                WHERE player_id = :pid AND season = :season
                ORDER BY games_played DESC
            """), {"pid": pid, "season": season}).fetchall()

            primary_id = rows[0][0]
            total_gp = sum(r[1] for r in rows if r[1])

            def weighted_avg(field_idx):
                vals = [(r[field_idx] or 0, r[1] or 0) for r in rows if r[1]]
                if not vals or sum(v[1] for v in vals) == 0:
                    return rows[0][field_idx]
                return round(sum(v[0] * v[1] for v in vals) / sum(v[1] for v in vals), 3)

            db.execute(text("""
                UPDATE player_data SET
                    games_played = :gp,
                    minutes_per_game = :mpg, points_per_game = :ppg,
                    rebounds_per_game = :rpg, assists_per_game = :apg,
                    steals_per_game = :spg, blocks_per_game = :bpg,
                    turnovers_per_game = :tpg,
                    fg_made_per_game = :fgm, fg_attempted_per_game = :fga,
                    fg_percentage = :fg_pct,
                    three_made_per_game = :fg3m, three_attempted_per_game = :fg3a,
                    three_percentage = :fg3_pct,
                    ft_made_per_game = :ftm, ft_attempted_per_game = :fta,
                    ft_percentage = :ft_pct,
                    true_shooting_pct = :ts_pct, effective_fg_pct = :efg_pct,
                    usage_rate = :usg, assist_pct = :ast_pct,
                    rebound_pct = :reb_pct, steal_pct = :stl_pct,
                    block_pct = :blk_pct, turnover_pct = :tov_pct
                WHERE id = :id
            """), {
                "id": primary_id, "gp": total_gp,
                "mpg": weighted_avg(2), "ppg": weighted_avg(3),
                "rpg": weighted_avg(4), "apg": weighted_avg(5),
                "spg": weighted_avg(6), "bpg": weighted_avg(7),
                "tpg": weighted_avg(8), "fgm": weighted_avg(9),
                "fga": weighted_avg(10), "fg_pct": weighted_avg(11),
                "fg3m": weighted_avg(12), "fg3a": weighted_avg(13),
                "fg3_pct": weighted_avg(14), "ftm": weighted_avg(15),
                "fta": weighted_avg(16), "ft_pct": weighted_avg(17),
                "ts_pct": weighted_avg(18), "efg_pct": weighted_avg(19),
                "usg": weighted_avg(20), "ast_pct": weighted_avg(21),
                "reb_pct": weighted_avg(22), "stl_pct": weighted_avg(23),
                "blk_pct": weighted_avg(24), "tov_pct": weighted_avg(25),
            })

            other_ids = [r[0] for r in rows[1:]]
            if other_ids:
                db.execute(text(f"DELETE FROM player_data WHERE id IN ({','.join(str(i) for i in other_ids)})"))

        db.commit()
        print(f"  合并完成")

        # 2. 合并同名球员的 player_data（先合并数据，再删重复 player）
        print("\n=== Step 2: 合并同名球员 ===")
        result = db.execute(text("""
            SELECT player_name, COUNT(*) as cnt
            FROM player
            GROUP BY player_name
            HAVING cnt > 1
        """))
        duplicates = [(row[0], row[1]) for row in result]
        print(f"发现 {len(duplicates)} 个重复球员名")

        fixed = 0
        for player_name, count in duplicates:
            players = db.execute(text("""
                SELECT player_id, team_id FROM player
                WHERE player_name = :name
                ORDER BY player_id DESC
            """), {"name": player_name}).fetchall()

            canonical_pid = players[0][0]
            other_pids = [p[0] for p in players[1:]]

            for other_pid in other_pids:
                # 获取该 player_id 的所有 player_data
                other_data = db.execute(text("""
                    SELECT season, games_played FROM player_data
                    WHERE player_id = :pid
                """), {"pid": other_pid}).fetchall()

                for od_season, od_gp in other_data:
                    # 检查 canonical 是否已有该赛季
                    existing = db.execute(text("""
                        SELECT id FROM player_data
                        WHERE player_id = :pid AND season = :season
                    """), {"pid": canonical_pid, "season": od_season}).fetchone()

                    if existing:
                        # canonical 已有该赛季，删除 other 的（已在 step1 聚合过）
                        db.execute(text("""
                            DELETE FROM player_data
                            WHERE player_id = :pid AND season = :season
                        """), {"pid": other_pid, "season": od_season})
                    else:
                        # canonical 没有该赛季，直接转移
                        db.execute(text("""
                            UPDATE player_data SET player_id = :canonical
                            WHERE player_id = :other AND season = :season
                        """), {"canonical": canonical_pid, "other": other_pid, "season": od_season})

                # 删除 other player 记录
                db.execute(text("DELETE FROM player WHERE player_id = :pid"), {"pid": other_pid})

            fixed += 1

        db.commit()
        print(f"  合并 {fixed} 个重复球员")

        # 3. 验证结果
        print("\n=== 清理结果 ===")
        result = db.execute(text("SELECT COUNT(*) FROM player"))
        print(f"球员记录: {result.scalar()}")

        result = db.execute(text("SELECT COUNT(DISTINCT player_name) FROM player"))
        print(f"唯一球员名: {result.scalar()}")

        result = db.execute(text("SELECT COUNT(*) FROM player_data"))
        print(f"球员赛季数据: {result.scalar()}")

        result = db.execute(text("""
            SELECT season, COUNT(*) FROM player_data GROUP BY season ORDER BY season
        """))
        print("各赛季球员数:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # 验证无重复
        result = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT player_id, season, COUNT(*) c
                FROM player_data GROUP BY player_id, season HAVING c > 1
            ) t
        """))
        print(f"\n剩余重复: {result.scalar()}")

    finally:
        db.close()


if __name__ == "__main__":
    cleanup()
