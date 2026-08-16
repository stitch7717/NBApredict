"""
导入历史伤病数据到 injury_record 表。

两个数据源:
  1. tylerferguson/NBAinjuries 数据集 (data/injuries.rda, 2012-13..2019-20):
     有精确 DateInjured/DateReturned/GamesMissed/BodyPart/Description
  2. basketball-reference 年度伤病归档 (injuries.fcgi?year=YYYY, 2021-2026):
     Player/Team/Update/Description（无复出日期，return_date 置 NULL）

用法:
    python scripts/import_injuries.py [--skip-bbref]
"""
import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pyreadr
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import InjuryRecord, Player, Team

RDA_FILE = Path(__file__).resolve().parent.parent / "data" / "injuries.rda"

SEASON_RANGES = {
    "2016-17": ("2016-10-01", "2017-06-30"),
    "2017-18": ("2017-10-01", "2018-06-30"),
    "2018-19": ("2018-10-01", "2019-06-30"),
    "2019-20": ("2019-10-01", "2020-10-15"),
    "2020-21": ("2020-12-01", "2021-07-31"),
    "2021-22": ("2021-10-01", "2022-06-30"),
    "2022-23": ("2022-10-01", "2023-06-30"),
    "2023-24": ("2023-10-01", "2024-06-30"),
    "2024-25": ("2024-10-01", "2025-06-30"),
    "2025-26": ("2025-10-01", "2026-06-30"),
}


def season_of(date_str: str) -> str:
    d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    for season, (start, end) in SEASON_RANGES.items():
        if start <= str(d) <= end:
            return season
    return ""


def import_rda():
    """导入 tylerferguson 数据集（2016-17..2019-20）"""
    if not RDA_FILE.exists():
        logger.error(f"数据集不存在: {RDA_FILE}（先下载 data/injuries.rda）")
        return
    df = list(pyreadr.read_r(str(RDA_FILE)).values())[0]

    with SessionLocal() as db:
        players = db.query(Player).all()
        name_map = {}
        for p in players:
            key = (p.player_name or "").strip().lower()
            if key and key not in name_map:
                name_map[key] = p
        teams = {t.team_id: t for t in db.query(Team).all()}
        team_by_tail = {}
        for t in teams.values():
            for key in (t.abbreviation, t.team_name_en, t.team_name):
                if key:
                    team_by_tail[key.strip().lower()] = t.team_id

        def to_season(label: str) -> str:
            """'2016-2017' -> '2016-17'"""
            parts = str(label).split("-")
            if len(parts) == 2 and len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1][-2:]}"
            return str(label)

        added = skipped = 0
        seen = set()
        for _, row in df.iterrows():
            season = to_season(row.get("Season", ""))
            if season not in ("2016-17", "2017-18", "2018-19", "2019-20"):
                continue
            name = str(row.get("PlayerName", "")).strip().lower()
            player = name_map.get(name)
            if player is None:
                skipped += 1
                continue
            team_name = str(row.get("TeamName", "")).strip().lower()
            team_id = team_by_tail.get(team_name)
            inj_date = row.get("DateInjured")
            ret_date = row.get("DateReturned")
            if pd.isna(inj_date):
                continue
            try:
                inj_d = datetime.strptime(str(inj_date)[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            ret_d = None
            if not pd.isna(ret_date):
                try:
                    ret_d = datetime.strptime(str(ret_date)[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            desc = str(row.get("InjuryDescription", ""))[:200]
            key = (player.player_id, inj_d, desc[:60])
            if key in seen:
                continue
            seen.add(key)
            db.add(InjuryRecord(
                player_id=player.player_id,
                team_id=team_id,
                season=season,
                injury_date=inj_d,
                return_date=ret_d,
                games_missed=int(row["GamesMissed"]) if not pd.isna(row.get("GamesMissed")) else None,
                body_part=str(row.get("BodyPartInjured", ""))[:50],
                description=desc,
                source="tylerferguson",
            ))
            added += 1
        db.commit()
        logger.info(f"tylerferguson 数据导入: 新增 {added}, 未匹配 {skipped}")


def import_bbref():
    """导入 bbref 年度伤病归档（2021-2026）"""
    from scripts.fetch_bbref_seasons import curl_fetch, flat, team_id_of, norm_name, delay

    with SessionLocal() as db:
        players = db.query(Player).all()
        name_map = {}
        for p in players:
            key = norm_name(p.player_name or p.player_name_en)
            if key and key not in name_map:
                name_map[key] = p
        abbr_map = {t.abbreviation: t.team_id for t in db.query(Team).all()}
        abbr_map.update({t.team_name_en: t.team_id for t in db.query(Team).all()})

    total_added = total_skip = 0
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        url = f"https://www.basketball-reference.com/friv/injuries.fcgi?year={year}"
        html = curl_fetch(url)
        if not html:
            logger.warning(f"  {year} 伤病页抓取失败")
            continue
        delay()
        try:
            tables = [flat(t) for t in pd.read_html(StringIO(html))]
            table = [t for t in tables if "Player" in list(t.columns) and "Description" in list(t.columns)]
        except ValueError:
            logger.warning(f"  {year} 伤病页解析失败")
            continue
        if not table:
            logger.warning(f"  {year} 无伤病表")
            continue
        table = table[0]

        added = 0
        seen = set()
        with SessionLocal() as db:
            for _, row in table.iterrows():
                name = str(row.get("Player", ""))
                nkey = norm_name(name)
                player = name_map.get(nkey)
                if player is None:
                    total_skip += 1
                    continue
                update = str(row.get("Update", ""))
                try:
                    inj_d = datetime.strptime(update[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                season = season_of(str(inj_d))
                team_id = team_id_of(abbr_map, row.get("Team", ""))
                desc = str(row.get("Description", ""))[:200]
                key = (player.player_id, inj_d, desc[:60])
                if key in seen:
                    continue
                seen.add(key)
                db.add(InjuryRecord(
                    player_id=player.player_id,
                    team_id=team_id,
                    season=season,
                    injury_date=inj_d,
                    return_date=None,
                    games_missed=None,
                    body_part=None,
                    description=desc,
                    source="bbref",
                ))
                added += 1
            db.commit()
        total_added += added
        logger.info(f"bbref {year}: 新增 {added}")
    logger.info(f"bbref 数据导入完成: 共 {total_added}, 未匹配 {total_skip}")


def main(skip_bbref: bool = False):
    logger.info("导入历史伤病数据...")
    import_rda()
    # 注意: injuries.fcgi 的 year 参数无效（返回当前伤病），历史数据只来自 tylerferguson
    if not skip_bbref:
        import_bbref()
    with SessionLocal() as db:
        from sqlalchemy import func
        rows = db.query(InjuryRecord).count()
        seasons = db.query(InjuryRecord.season, func.count()).group_by(InjuryRecord.season).all()
    logger.info(f"injury_record 共 {rows} 行")
    for s, c in sorted(seasons):
        logger.info(f"  {s}: {c} 行")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-bbref", action="store_true")
    args = parser.parse_args()
    main(skip_bbref=args.skip_bbref)
