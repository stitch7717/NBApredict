"""
导入 Kaggle 历史赔率数据集 (nba_2008-2026.csv) 到 odds_data 表。

数据来源: https://www.kaggle.com/datasets/cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
覆盖: 2007-08 .. 2025-26 赛季, 每场含让分(spread)/大小分(total)/胜负赔率(moneyline)/逐节比分

处理:
- 按 (日期, 主队, 客队) 匹配 game_record，写入 game_id/home_team_id/away_team_id
- 美国盘 moneyline (+190/-230) 换算隐含概率并去水归一化
- handicap_line 以主队视角: 主队让分为负
- 顺带把 game_record 的逐节比分(q1-q4+加时)回填（库内全为 NULL）
- 新增 odds_source 'kaggle_archive' 作为来源

用法:
    python scripts/import_kaggle_odds.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, OddsData, OddsSource

CSV_FILE = Path(__file__).resolve().parent.parent / "data" / "kaggle_odds" / "nba_2008-2026.csv"

ABBR_FIX = {"gs": "GSW", "no": "NOP", "utah": "UTA", "wsh": "WAS", "ny": "NYK", "sa": "SAS"}

TARGET_SEASONS = [
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25", "2025-26",
]


def season_of(year: int) -> str:
    """CSV 的 season 是赛季结束年（2008 = 2007-08 赛季）"""
    return f"{year - 1}-{str(year)[-2:]}"


def fix_abbr(abbr) -> str:
    a = str(abbr).strip().lower()
    return ABBR_FIX.get(a, a.upper())


def moneyline_prob(odds: float) -> float:
    """美国盘换算隐含概率"""
    if pd.isna(odds):
        return 0.0
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def main():
    if not CSV_FILE.exists():
        logger.error(f"数据文件不存在: {CSV_FILE}")
        return
    df = pd.read_csv(CSV_FILE)
    df = df[df["season"].map(season_of).isin(TARGET_SEASONS)].copy()
    logger.info(f"目标 10 赛季范围内共 {len(df)} 行")

    with SessionLocal() as db:
        from app.db.models import Team
        abbr_map = {t.abbreviation.upper(): t.team_id for t in db.query(Team).all()}
        games = db.query(GameRecord).all()
        game_index = {}
        for g in games:
            key = (str(g.game_date), g.home_team_id, g.away_team_id)
            if key not in game_index:
                game_index[key] = g

        # 赔率来源行
        source = db.query(OddsSource).filter(OddsSource.source_code == "kaggle_archive").first()
        if source is None:
            source = OddsSource(
                source_name="Kaggle 历史赔率数据集",
                source_code="kaggle_archive",
                source_url="https://www.kaggle.com/datasets/cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024",
                source_type="ARCHIVE",
                status="ACTIVE",
            )
            db.add(source)
            db.flush()

        # 清空旧赔率数据（幂等重跑）
        db.query(OddsData).delete()

        inserted = 0
        matched_q = 0
        unmatched = 0
        for _, row in df.iterrows():
            season = season_of(int(row["season"]))
            gdate = datetime.strptime(str(row["date"])[:10], "%Y-%m-%d").date()
            hid = abbr_map.get(fix_abbr(row["home"]))
            aid = abbr_map.get(fix_abbr(row["away"]))
            if not hid or not aid:
                unmatched += 1
                continue
            g = game_index.get((str(gdate), hid, aid))
            if g is None:
                unmatched += 1
                continue

            # 概率换算（去水）
            h_raw = moneyline_prob(row["moneyline_home"])
            a_raw = moneyline_prob(row["moneyline_away"])
            s = h_raw + a_raw
            h_prob = h_raw / s if s > 0 else 0.5
            a_prob = a_raw / s if s > 0 else 0.5

            # 让分（主队视角: 主队让分为负）
            spread = float(row["spread"]) if pd.notna(row["spread"]) else None
            if spread is not None:
                spread = -spread if str(row.get("whos_favored", "")).strip().lower() == "home" else spread

            db.add(OddsData(
                game_id=g.game_id,
                game_date=gdate,
                home_team_id=hid,
                away_team_id=aid,
                source_id=source.source_id,
                home_win_odds=float(row["moneyline_home"]) if pd.notna(row["moneyline_home"]) else None,
                away_win_odds=float(row["moneyline_away"]) if pd.notna(row["moneyline_away"]) else None,
                home_win_prob=round(h_prob, 4),
                away_win_prob=round(a_prob, 4),
                handicap_line=spread,
                total_line=float(row["total"]) if pd.notna(row["total"]) else None,
                data_quality="NORMAL",
            ))
            inserted += 1

            # 回填逐节比分（仅当库内为 NULL）
            if g.home_q1_score is None and hasattr(g, "home_q1_score"):
                g.home_q1_score = int(row["q1_home"]) if pd.notna(row["q1_home"]) else None
                g.home_q2_score = int(row["q2_home"]) if pd.notna(row["q2_home"]) else None
                g.home_q3_score = int(row["q3_home"]) if pd.notna(row["q3_home"]) else None
                g.home_q4_score = int(row["q4_home"]) if pd.notna(row["q4_home"]) else None
                g.away_q1_score = int(row["q1_away"]) if pd.notna(row["q1_away"]) else None
                g.away_q2_score = int(row["q2_away"]) if pd.notna(row["q2_away"]) else None
                g.away_q3_score = int(row["q3_away"]) if pd.notna(row["q3_away"]) else None
                g.away_q4_score = int(row["q4_away"]) if pd.notna(row["q4_away"]) else None
                matched_q += 1

        db.commit()
        logger.info(f"赔率导入: {inserted} 行, 未匹配 {unmatched}, 逐节比分回填 {matched_q} 场")


if __name__ == "__main__":
    main()
