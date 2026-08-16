"""
补全 team_data 缺失列（bbref 联赛页 + Kaggle team misc 数据集）:

来源 1 (bbref 联赛页 /leagues/NBA_{year}.html):
  - Team Per Game 表 -> assists/rebounds/turnovers/steals/blocks/fg%/3p%/ft%/进攻篮板
  - Misc 表扩展 -> eFG%/TS%
  - Opponent Per Game 表 -> opponent_fg_percentage/opponent_three_pct

来源 2 (Kaggle chrismunch/nba-game-team-statistics, games_misc.csv):
  - FBPs -> fast_break_points, 2nd PTS -> second_chance_points, PITP -> points_in_paint
  （按 日期+主客队 匹配 game_record 定赛季，聚合为赛季场均）

只补当前为 NULL/0 的值，不覆盖已有数据。

用法:
    python scripts/backfill_team_advanced.py
"""
import sys
import numpy as np
import time
from collections import defaultdict
from datetime import datetime
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, Team, TeamData
from scripts.fetch_bbref_seasons import (
    BBREF_YEAR, SEASONS_10, curl_fetch, flat, delay, team_id_of,
)

MISC_CSV = Path(__file__).resolve().parent.parent / "data" / "kaggle_teammisc" / "cumulative_scraped" / "games_misc.csv"

# bbref 联赛页表格列映射: (bbref列, team_data列)
PER_GAME_MAP = [
    ("FG%", "fg_percentage"), ("3P%", "three_percentage"), ("FT%", "ft_percentage"),
    ("ORB", "offensive_rebounds"), ("TRB", "rebounds_per_game"), ("AST", "assists_per_game"),
    ("STL", "steals_per_game"), ("BLK", "blocks_per_game"), ("TOV", "turnovers_per_game"),
]
MISC_MAP = [("eFG%", "effective_fg_pct"), ("TS%", "true_shooting_pct")]
OPP_MAP = [("FG%", "opponent_fg_percentage"), ("3P%", "opponent_three_pct")]


def num(v):
    try:
        if pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def backfill_bbref():
    logger.info("来源 1: bbref 联赛页补全...")
    with SessionLocal() as db:
        abbr_map = {}
        for t in db.query(Team).all():
            for key in (t.abbreviation, t.team_name_en, t.team_name):
                if key:
                    abbr_map[key.strip()] = t.team_id  # 保持原始大小写，team_id_of 尾词匹配依赖它

    for season in SEASONS_10:
        year = BBREF_YEAR[season]
        html = curl_fetch(f"https://www.basketball-reference.com/leagues/NBA_{year}.html")
        if not html:
            logger.warning(f"  [{season}] 页面抓取失败")
            continue
        delay()
        try:
            tables = [flat(t) for t in pd.read_html(StringIO(html))]
        except ValueError:
            logger.warning(f"  [{season}] 解析失败")
            continue

        # 战绩表: 队名 -> 场均得分（用于区分 Team 表与 Opponent 表）
        standings_ps = {}
        for tb in tables:
            if "PS/G" not in list(tb.columns):
                continue
            col0 = list(tb.columns)[0]
            for _, row in tb.iterrows():
                name = str(row.get(col0, "")).rstrip("*").strip()
                if "Division" in name or "Conference" in name:
                    continue  # 分区小标题行
                val = num(row["PS/G"])
                if val is None:
                    continue
                standings_ps[name] = val

        # 结构相同的 per-game 表（Team 与 Opponent 列名一样），用 PTS 列与战绩 PS/G 的相关性区分
        cand = [t for t in tables if "AST" in list(t.columns) and "PTS" in list(t.columns) and "FG" in list(t.columns)]
        team_table = opp_table = None
        best_r, worst_r = -2.0, 2.0
        for tb in cand:
            if "Tm" not in list(tb.columns):
                continue
            xs, ys = [], []
            for _, row in tb.iterrows():
                name = str(row.get("Tm", "")).rstrip("*").strip()
                if name in standings_ps and pd.notna(row.get("PTS")):
                    xs.append(standings_ps[name])
                    ys.append(float(row["PTS"]))
            if len(xs) < 20:
                continue
            r = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 else 0.0
            if r > best_r:
                best_r, team_table = r, tb
            if r < worst_r:
                worst_r, opp_table = r, tb

        misc_tables = [t for t in tables if "Pace" in list(t.columns) and "ORtg" in list(t.columns)]

        with SessionLocal() as db:
            tds = {td.team_id: td for td in db.query(TeamData).filter(TeamData.season == season).all()}
            if not tds:
                continue
            updated = 0

            def apply_rows(table, col_map):
                nonlocal updated
                if table is None:
                    return
                for _, row in table.iterrows():
                    tid = team_id_of(abbr_map, row.get("Tm", row.get("Team", "")))
                    if not tid or tid not in tds:
                        continue
                    td = tds[tid]
                    for bcol, dcol in col_map:
                        if bcol not in row:
                            continue
                        val = row[bcol]
                        if isinstance(val, pd.Series):  # 重复列名（如两个 eFG%）取第一个
                            val = val.iloc[0]
                        val = num(val)
                        cur = getattr(td, dcol)
                        if val is not None and (cur is None or cur == 0):
                            setattr(td, dcol, round(val, 3))
                            updated += 1

            apply_rows(team_table, PER_GAME_MAP)
            for mtb in misc_tables:
                apply_rows(mtb, MISC_MAP)
            apply_rows(opp_table, OPP_MAP)
            db.commit()
            logger.info(f"  [{season}] 更新 {updated} 个值 (team表r={best_r:.2f}, opp表r={worst_r:.2f})")


def backfill_kaggle_misc():
    if not MISC_CSV.exists():
        logger.warning("games_misc.csv 不存在，跳过 Kaggle misc 补全")
        return
    logger.info("来源 2: Kaggle games_misc.csv 补全快攻/内线/二次进攻...")
    df = pd.read_csv(MISC_CSV)
    logger.info(f"  {len(df)} 行")

    with SessionLocal() as db:
        abbr_map = {t.abbreviation.upper(): t.team_id for t in db.query(Team).all()}
        # 内联 team_id: NBA 10位id -> 内部id（复用 fetch_nba_data 的映射）
        from scripts.fetch_nba_data import NBA_TO_INTERNAL
        games = db.query(GameRecord).all()
        game_index = {}
        for g in games:
            key = (g.game_date, g.home_team_id, g.away_team_id)
            if key not in game_index:
                game_index[key] = g

        # 按 (内部队, 赛季) 聚合: 场次 + 三列累计
        agg = defaultdict(lambda: {"n": 0, "fb": 0.0, "sc": 0.0, "paint": 0.0})
        matched = 0
        for _, row in df.iterrows():
            nba_tid = row.get("TEAM_ID")
            tid = NBA_TO_INTERNAL.get(int(nba_tid)) if pd.notna(nba_tid) else None
            if not tid:
                continue
            try:
                gdate = datetime.strptime(str(row.get("Game Date", "")).strip(), "%m/%d/%Y").date()
            except ValueError:
                continue
            # 该行是主队还是客队: Match Up 格式 "CHI @ MIA"(客队视角) / "MIA vs. CHI"(主队视角)
            mu = str(row.get("Match Up", ""))
            is_home = " vs. " in mu
            if is_home:
                g = game_index.get((gdate, tid, None)) if False else None
                # 需要对手来定位，简化: 用 GAME_ID 附近的日期+任意对阵匹配
                candidates = [v for k, v in game_index.items() if k[0] == gdate and (k[1] == tid or k[2] == tid)]
                g = candidates[0] if candidates else None
            else:
                candidates = [v for k, v in game_index.items() if k[0] == gdate and (k[1] == tid or k[2] == tid)]
                g = candidates[0] if candidates else None
            if g is None:
                continue
            a = agg[(tid, g.season)]
            a["n"] += 1
            a["fb"] += num(row.get("FBPs")) or 0
            a["sc"] += num(row.get("2nd PTS")) or 0
            a["paint"] += num(row.get("PITP")) or 0
            matched += 1
        logger.info(f"  匹配 {matched} 行")

        updated = 0
        for (tid, season), a in agg.items():
            td = db.query(TeamData).filter(TeamData.team_id == tid, TeamData.season == season).first()
            if td is None:
                continue
            if a["n"] == 0:
                continue
            if (td.fast_break_points is None or td.fast_break_points == 0) and a["fb"]:
                td.fast_break_points = round(a["fb"] / a["n"], 1)
                updated += 1
            if (td.second_chance_points is None or td.second_chance_points == 0) and a["sc"]:
                td.second_chance_points = round(a["sc"] / a["n"], 1)
                updated += 1
            if (td.points_in_paint is None or td.points_in_paint == 0) and a["paint"]:
                td.points_in_paint = round(a["paint"] / a["n"], 1)
                updated += 1
        db.commit()
        logger.info(f"  更新 {updated} 个值")


def backfill_player_net_rating():
    with SessionLocal() as db:
        from sqlalchemy import text
        r = db.execute(text(
            "UPDATE player_data SET net_rating = ROUND(offensive_rating - defensive_rating, 1) "
            "WHERE (net_rating IS NULL OR net_rating = 0) "
            "AND offensive_rating IS NOT NULL AND defensive_rating IS NOT NULL"
        ))
        db.commit()
        logger.info(f"player_data.net_rating 补全 {r.rowcount} 行")


if __name__ == "__main__":
    backfill_player_net_rating()
    backfill_bbref()
    backfill_kaggle_misc()
    logger.info("补全完成")
