"""
NBA 数据校验脚本 — 三部分:
  A. 完整性检查（纯 DB，秒级）: 场次/日期窗口/重复/类型一致性/名单/空值审计
  B. 交叉验证: 比赛分数 vs ESPN 事件缓存（抽样 100 场）
  C. bbref 独立源比对（--with-bbref）: 每赛季球队 W/L vs 库内 team_data（最强独立校验）
     + 2023-24 球员场均数据抽样比对（库内 stats.nba.com 旧数据 vs bbref）

用法:
    python scripts/verify_nba_data.py [--with-bbref] [--sample-size 100]
输出: 控制台 + logs/verify_report.txt；发现 FAIL 时退出码非 0。
"""
import json
import random
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, Player, PlayerData, PlayerRoster, SeriesStar, TeamData

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ESPN_CACHE = DATA_DIR / "espn_events_cache.json"

# 常规赛场次预期（2019-20 因疫情停摆 1059 场；2020-21 为 72 场赛季 1080 场；
# 2020-21 起每年另有 4~6 场 play-in 附加赛被 ESPN 归为常规赛类型，容差 ±8）
EXPECTED_REGULAR = {
    "2016-17": 1230, "2017-18": 1230, "2018-19": 1230,
    "2019-20": 1059, "2020-21": 1080, "2021-22": 1230,
    "2022-23": 1230, "2023-24": 1230, "2024-25": 1230, "2025-26": 1230,
}
REGULAR_TOLERANCE = 8
SEASON_DATE_RANGES = {
    "2016-17": ("2016-10-01", "2017-06-30"), "2017-18": ("2017-10-01", "2018-06-30"),
    "2018-19": ("2018-10-01", "2019-06-30"), "2019-20": ("2019-10-01", "2020-10-15"),
    "2020-21": ("2020-12-01", "2021-07-31"), "2021-22": ("2021-10-01", "2022-06-30"),
    "2022-23": ("2022-10-01", "2023-06-30"), "2023-24": ("2023-10-01", "2024-06-30"),
    "2024-25": ("2024-10-01", "2025-06-30"), "2025-26": ("2025-10-01", "2026-06-30"),
}

FAILS = []
WARNS = []


def fail(msg):
    FAILS.append(msg)
    logger.error(f"[FAIL] {msg}")


def warn(msg):
    WARNS.append(msg)
    logger.warning(f"[WARN] {msg}")


def check_a_integrity():
    logger.info("=" * 60)
    logger.info("A. 完整性检查")
    logger.info("=" * 60)
    with SessionLocal() as db:
        games = db.query(GameRecord).all()
        by_season = {}
        for g in games:
            by_season.setdefault(g.season, []).append(g)

        for season in sorted(by_season):
            rows = by_season[season]
            reg = [g for g in rows if g.game_type == "Regular Season"]
            po = [g for g in rows if g.game_type == "Playoffs"]
            expected = EXPECTED_REGULAR.get(season)
            if expected is not None and abs(len(reg) - expected) > REGULAR_TOLERANCE:
                fail(f"{season} 常规赛 {len(reg)} 场，预期 {expected}±{REGULAR_TOLERANCE}")
            else:
                logger.info(f"{season}: 常规赛 {len(reg)}, 季后赛 {len(po)}")
            if season in SEASON_DATE_RANGES:
                d1 = datetime.strptime(SEASON_DATE_RANGES[season][0], "%Y-%m-%d").date()
                d2 = datetime.strptime(SEASON_DATE_RANGES[season][1], "%Y-%m-%d").date()
                out = [g for g in rows if not (d1 <= g.game_date <= d2)]
                if out:
                    fail(f"{season} 有 {len(out)} 场日期超出窗口: {out[0].game_date}")
            types = {g.game_type for g in rows}
            if types - {"Regular Season", "Playoffs"}:
                fail(f"{season} 存在异常 game_type: {types}")
            bad_win = [g for g in rows if g.home_win != (1 if g.home_score > g.away_score else 0)]
            if bad_win:
                fail(f"{season} {len(bad_win)} 场 home_win 与比分不一致")
            bad_score = [g for g in rows if (g.home_score or 0) <= 0 or (g.away_score or 0) <= 0]
            if bad_score:
                fail(f"{season} {len(bad_score)} 场比分为非正数")
            dup = [k for k, c in Counter((g.game_date, g.home_team_id, g.away_team_id) for g in rows).items() if c > 1]
            if dup:
                fail(f"{season} {len(dup)} 组重复比赛")

        # 名单检查
        logger.info("-" * 40)
        for season in sorted({r.season for r in db.query(PlayerRoster.season).all()}):
            cnt = db.query(PlayerRoster).filter(PlayerRoster.season == season).count()
            pos_filled = db.query(PlayerRoster).filter(
                PlayerRoster.season == season,
                PlayerRoster.position.isnot(None),
                PlayerRoster.position != "",
            ).count()
            rate = pos_filled / cnt if cnt else 0
            if cnt < 400:
                fail(f"player_roster {season} 仅 {cnt} 行")
            elif rate < 0.98:
                fail(f"player_roster {season} 位置填充率 {rate:.1%}")
            else:
                logger.info(f"player_roster {season}: {cnt} 行, 位置填充率 {rate:.1%}")

        # 球员空值审计（字符串列额外检查空串；日期/数值列只查 NULL）
        logger.info("-" * 40)
        total_p = db.query(Player).count()
        for col in ["position", "height", "weight", "age", "birth_date", "jersey_number"]:
            col_obj = getattr(Player, col)
            cond = col_obj.is_(None)
            if str(col_obj.type).lower().startswith("varchar"):
                cond = cond | (col_obj == "")
            empty = db.query(Player).filter(cond).count()
            logger.info(f"player.{col}: {empty}/{total_p} 空")
        pd_total = db.query(PlayerData).count()
        for col in ["per", "bpm", "vorp", "win_shares"]:
            col_obj = getattr(PlayerData, col)
            zero = db.query(PlayerData).filter((col_obj.is_(None)) | (col_obj == 0)).count()
            logger.info(f"player_data.{col}: {zero}/{pd_total} 零或空")

        # 引用完整性
        dangling = 0
        valid = {g.game_id for g in db.query(GameRecord.game_id).all()}
        for ss in db.query(SeriesStar).filter(SeriesStar.key_game_id.isnot(None)).all():
            if ss.key_game_id not in valid:
                dangling += 1
        if dangling:
            fail(f"series_star 有 {dangling} 条悬空 key_game_id")

        # team_data 完整性
        td_seasons = [s for (s,) in db.query(TeamData.season).all()]
        logger.info(f"team_data 赛季: {sorted(td_seasons)}")
        for s in sorted(set(td_seasons)):
            cnt = db.query(TeamData).filter(TeamData.season == s).count()
            if cnt != 30:
                fail(f"team_data {s} 只有 {cnt} 队")


def check_b_espn_cross(sample_size: int = 100):
    logger.info("=" * 60)
    logger.info("B. 比赛分数 vs ESPN 事件缓存交叉验证")
    logger.info("=" * 60)
    if not ESPN_CACHE.exists():
        warn("无 ESPN 事件缓存，跳过")
        return
    cache = json.loads(ESPN_CACHE.read_text(encoding="utf-8"))
    event_index = {}
    for season, events in cache.items():
        for key, ev in events.items():
            event_index[key] = ev

    with SessionLocal() as db:
        games = db.query(GameRecord).all()
    if not games:
        fail("game_record 为空")
        return
    sample = random.sample(games, min(sample_size, len(games)))
    mismatch = 0
    for g in sample:
        key = f"{g.game_date}|{g.home_team_id}|{g.away_team_id}"
        ev = event_index.get(key)
        if ev is None:
            mismatch += 1
            logger.warning(f"  库内比赛无对应 ESPN 事件: {key}")
            continue
        if (g.home_score, g.away_score) != (ev["home_score"], ev["away_score"]):
            mismatch += 1
            logger.warning(f"  比分不一致: {key} DB={g.home_score}-{g.away_score} ESPN={ev['home_score']}-{ev['away_score']}")
        if g.season != ev["season"]:
            mismatch += 1
            logger.warning(f"  赛季标签不一致: {key} DB={g.season} ESPN={ev['season']}")
    if mismatch:
        fail(f"ESPN 交叉验证: {mismatch}/{len(sample)} 不一致")
    else:
        logger.info(f"ESPN 交叉验证通过: {len(sample)} 场抽样全部一致")


def check_c_bbref():
    """bbref 独立源比对: 每赛季球队 W/L + 2023-24 球员场均抽样"""
    from scripts.fetch_bbref_seasons import (
        BBREF_YEAR, BASE, SEASONS_10, curl_fetch, flat, delay, norm_name,
    )
    from io import StringIO
    import pandas as pd

    logger.info("=" * 60)
    logger.info("C. bbref 独立源比对（球队 W/L + 球员抽样）")
    logger.info("=" * 60)

    with SessionLocal() as db:
        from app.db.models import Team
        abbr_map = {t.abbreviation: t.team_id for t in db.query(Team).all()}
        rev_map = {v: k for k, v in abbr_map.items()}

    # C1: 每赛季球队 W/L
    for season in SEASONS_10:
        year = BBREF_YEAR[season]
        html = curl_fetch(f"{BASE}/leagues/NBA_{year}.html")
        if not html:
            warn(f"[{season}] bbref 战绩页抓取失败，跳过")
            delay()
            continue
        try:
            tables = [flat(t) for t in pd.read_html(StringIO(html))]
            standings = [t for t in tables if "W" in list(t.columns) and "L" in list(t.columns) and "PS/G" in list(t.columns)]
        except Exception as e:
            warn(f"[{season}] bbref 战绩解析失败: {e}")
            delay()
            continue
        delay()
        if not standings:
            warn(f"[{season}] bbref 无战绩表")
            continue
        with SessionLocal() as db:
            tds = {td.team_id: td for td in db.query(TeamData).filter(TeamData.season == season).all()}
        # 东西两个战绩表第一列名不同，逐表处理
        from scripts.fetch_bbref_seasons import team_id_of
        mism = 0
        for df in standings:
            abbr_col = list(df.columns)[0]
            for _, row in df.iterrows():
                tid = team_id_of(abbr_map, row.get(abbr_col, ""))
                if not tid or tid not in tds:
                    continue
                td = tds[tid]
                w, l = int(row.get("W") or 0), int(row.get("L") or 0)
                if (td.wins, td.losses) != (w, l):
                    mism += 1
                    logger.warning(f"  [{season}] {rev_map[tid]} W/L 不一致: DB={td.wins}-{td.losses} bbref={w}-{l}")
        if mism:
            fail(f"[{season}] {mism} 队 W/L 与 bbref 不一致")
        else:
            logger.info(f"[{season}] 30 队 W/L 与 bbref 一致")

    # C2: 2023-24 球员场均抽样（库内 stats.nba.com 旧数据 vs bbref）
    season = "2023-24"
    year = BBREF_YEAR[season]
    html = curl_fetch(f"{BASE}/leagues/NBA_{year}_per_game.html")
    if not html:
        warn("bbref 球员页抓取失败，跳过球员抽样")
        return
    try:
        tables = [flat(t) for t in pd.read_html(StringIO(html))]
        per_game = pd.concat([t for t in tables if "Player" in list(t.columns) and "PTS" in list(t.columns)], ignore_index=True)
        per_game = per_game[per_game["Rk"] != "Rk"]
    except Exception as e:
        warn(f"bbref 球员页解析失败: {e}")
        return
    delay()

    with SessionLocal() as db:
        pd_rows = db.query(PlayerData).filter(PlayerData.season == season).all()
        name_map = {p.player_id: (p.player_name or p.player_name_en or "") for p in db.query(Player).all()}
    sample = random.sample(pd_rows, min(30, len(pd_rows)))
    mism = checked = 0
    for pd_row in sample:
        name = name_map.get(pd_row.player_id, "")
        nkey = norm_name(name)
        bbref_rows = per_game[per_game["Player"].map(norm_name) == nkey]
        if bbref_rows.empty:
            continue
        row = bbref_rows.iloc[0]
        checked += 1
        for db_val, bbr_col, label in [
            (pd_row.points_per_game, "PTS", "得分"),
            (pd_row.rebounds_per_game, "TRB", "篮板"),
            (pd_row.assists_per_game, "AST", "助攻"),
        ]:
            try:
                bbr_val = float(row[bbr_col])
            except (TypeError, ValueError):
                continue
            if db_val is None or abs(db_val - bbr_val) > 0.6:
                mism += 1
                logger.warning(f"  [{season}] {name} {label}: DB={db_val} bbref={bbr_val}")
    if checked and mism / (checked * 3) > 0.05:
        fail(f"球员抽样: {mism} 处不一致 / {checked} 人")
    else:
        logger.info(f"球员抽样通过: {checked} 人比对, {mism} 处不一致")


def main(sample_size: int = 100, with_bbref: bool = False):
    random.seed(42)
    logger.info("NBA 数据校验开始")
    check_a_integrity()
    check_b_espn_cross(sample_size)
    if with_bbref:
        check_c_bbref()

    report = "\n".join(FAILS)
    if FAILS:
        logger.error(f"\n校验失败 {len(FAILS)} 项，警告 {len(WARNS)} 项")
        (Path(__file__).resolve().parent.parent / "logs" / "verify_report.txt").write_text(
            "FAILS:\n" + report + "\n\nWARNS:\n" + "\n".join(WARNS), encoding="utf-8"
        )
        sys.exit(1)
    logger.info(f"\n全部校验通过（警告 {len(WARNS)} 项）")
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--with-bbref", action="store_true", help="追加 bbref 独立源比对（耗时较长）")
    args = parser.parse_args()
    main(sample_size=args.sample_size, with_bbref=args.with_bbref)
