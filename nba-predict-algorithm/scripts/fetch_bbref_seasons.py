"""
从 basketball-reference 采集 10 个赛季的球员数据、球队数据和球员名单
（stats.nba.com 被 Akamai 封锁后采用的替代数据源）

数据源页面（每个赛季 4 页，共 40 页 + 30 页现役名单 = 70 页）:
- /leagues/NBA_{year}_per_game.html   球员场均数据（含 Pos/Tm/Age/GP）
- /leagues/NBA_{year}_advanced.html   高阶数据（PER/TS%/USG%/WS/BPM/VORP/占比）
- /leagues/NBA_{year}_per_poss.html   每百回合（ORtg/DRtg）
- /leagues/NBA_{year}.html            球队战绩（W/L/PS/G/PA/G/SRS）
- /teams/{TLA}/{year}.html            现役名单（身高/体重/生日/球衣号，仅当前赛季）

注意:
- bbref 有 TLS 指纹检测，Python requests 会被 403，必须用 curl 子进程抓取
- bbref 礼貌爬取约定: 每请求间隔 >= 3 秒
- 已有数据的赛季默认跳过（--force 可覆盖），数据源为 stats.nba.com 的
  2022-23..2025-26 四个赛季不会被覆盖，仅做对比校验
"""
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from bs4 import BeautifulSoup
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, PlayerRoster, Team, TeamData

# 10 个赛季: 2016-17 .. 2025-26（bbref 年份取赛季后两年份）
SEASONS_10 = [
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25", "2025-26",
]

BBREF_YEAR = {s: f"{s[:2]}{s[5:7]}" for s in SEASONS_10}  # "2016-17" -> "2017"

PROXY = "http://127.0.0.1:7897"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_DELAY = 7.0  # bbref 礼貌间隔（过快会触发 Cloudflare 质询）

BASE = "https://www.basketball-reference.com"


def curl_fetch(url: str, retries: int = 4) -> str:
    """用 curl 子进程抓取页面（Python requests 的 TLS 指纹会被 bbref 拦截）

    Cloudflare 质询页（"Just a moment..."）出现时等待更久再重试。
    """
    for attempt in range(retries):
        try:
            r = subprocess.run(
                ["curl", "-s", "-x", PROXY, "-A", USER_AGENT, "--max-time", "60", url],
                capture_output=True, timeout=90,
            )
            html = r.stdout.decode("utf-8", errors="replace")
            if len(html) > 10000 and "Just a moment" not in html and "<html" in html.lower():
                return html
            logger.warning(f"  响应异常/质询页 ({len(html)}B)，第 {attempt + 1} 次重试: {url[:80]}")
        except Exception as e:
            logger.warning(f"  curl 失败 ({e})，重试 {attempt + 1}: {url[:80]}")
        time.sleep(20 * (attempt + 1))
    return ""


def delay():
    time.sleep(REQUEST_DELAY)


def norm_name(name: str) -> str:
    """名字规范化: 去重音 + 小写（'Nikola Jokić' -> 'nikola jokic'）"""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def bbref_slug_map(html: str) -> dict:
    """从球员表 HTML 提取 球员显示名 -> bbref slug 映射（用于新球员 nba_id）"""
    soup = BeautifulSoup(html, "html.parser")
    mapping = {}
    for link in soup.find_all("a", href=re.compile(r"/players/[a-z]/[a-z0-9]+\.html")):
        slug = re.search(r"/players/[a-z]/([a-z0-9]+)\.html", link["href"])
        name = norm_name(link.get_text())
        if slug and name and name not in mapping:
            mapping[name] = slug.group(1)
    return mapping


def fallback_nba_id(nkey: str) -> str:
    """slug 缺失时的稳定兜底 ID（md5 前 10 位，跨运行幂等）"""
    import hashlib
    return "bbref_" + hashlib.md5(nkey.encode("utf-8")).hexdigest()[:10]


def fetch_player_pages(season: str):
    """抓取某赛季的 3 个球员数据页，返回合并 DataFrame 与 slug 映射"""
    year = BBREF_YEAR[season]
    pages = {"per_game": None, "advanced": None, "per_poss": None}
    slug_map = {}
    for kind in pages:
        url = f"{BASE}/leagues/NBA_{year}_{kind}.html"
        html = curl_fetch(url)
        if not html:
            logger.error(f"  [{season}] {kind} 页面抓取失败")
            continue
        tables = [flat(t) for t in pd.read_html(StringIO(html))]
        if kind == "per_game":
            matches = [t for t in tables if "Player" in list(t.columns) and "PTS" in list(t.columns)]
        elif kind == "advanced":
            matches = [t for t in tables if "Player" in list(t.columns) and "PER" in list(t.columns)]
        else:
            matches = [t for t in tables if "Player" in list(t.columns) and "ORtg" in list(t.columns)]
        # bbref 可能把球员表拆成多段 <table>，全部合并
        pages[kind] = pd.concat(matches, ignore_index=True) if matches else None
        slug_map.update(bbref_slug_map(html))
        delay()

    per_game = pages["per_game"]
    if per_game is None:
        return None, slug_map
    per_game = per_game[per_game["Rk"] != "Rk"].copy()
    # 去掉分段表重复的表头行和 League Average 汇总行
    per_game = per_game[~per_game["Player"].astype(str).isin(["Player", "League Average"])]

    # 合并 advanced 与 per_poss
    for kind, cols in [("advanced", ["PER", "TS%", "USG%", "WS", "BPM", "VORP", "AST%", "TRB%", "STL%", "BLK%", "TOV%"]),
                       ("per_poss", ["ORtg", "DRtg"])]:
        df = pages[kind]
        if df is None:
            continue
        df = df[df["Rk"] != "Rk"].copy()
        key = df["Player"].map(norm_name) + "_" + df["Tm"].astype(str)
        per_game["_key"] = per_game["Player"].map(norm_name) + "_" + per_game["Tm"].astype(str)
        df["_key"] = key
        merge_cols = ["_key"] + [c for c in cols if c in df.columns]
        per_game = per_game.merge(df[merge_cols], on="_key", how="left")
        per_game = per_game.drop(columns=["_key"])

    per_game["_norm"] = per_game["Player"].map(norm_name)
    per_game["_slug"] = per_game["_norm"].map(slug_map).fillna("")
    return per_game, slug_map


def flat(df: pd.DataFrame) -> pd.DataFrame:
    """展平 MultiIndex 列名，并把新版 'Team' 列名统一为旧版 'Tm'"""
    df = df.copy()
    df.columns = [c[-1] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={"Team": "Tm"})
    return df


def num(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def int_or_null(val):
    try:
        if pd.isna(val):
            return None
        return int(float(val))
    except (TypeError, ValueError):
        return None


def cm_from_bbref(h: str) -> float:
    """'6-7' -> 200.66 cm；无法解析返回 None"""
    m = re.match(r"^(\d+)-(\d+)$", str(h).strip())
    if not m:
        return None
    return round((int(m.group(1)) * 12 + int(m.group(2))) * 2.54, 1)


def kg_from_lbs(w) -> float:
    try:
        w = float(w)
        return round(w * 0.4536, 1)
    except (TypeError, ValueError):
        return None


def load_players(db) -> dict:
    """规范化名字 -> Player 映射 + 已有 nba_id 集合"""
    players = db.query(Player).all()
    name_map = {}
    for p in players:
        key = norm_name(p.player_name or p.player_name_en)
        if key and key not in name_map:
            name_map[key] = p
    return name_map


def team_abbr_map(db) -> dict:
    """bbref 队名（全名/缩写/尾词）-> 内部 team_id

    库内 team_name_en 是简称（"Celtics"），bbref 战绩表是全名（"Boston Celtics*"），
    用尾词（最后一个单词）做桥接，30 队尾词均唯一。
    """
    mapping = {}
    for t in db.query(Team).all():
        for key in (t.abbreviation, t.team_name, t.team_name_en):
            if key:
                mapping[key] = t.team_id
    return mapping


def team_id_of(mapping: dict, name: str):
    """按 全名/末两词/尾词/缩写 解析内部 team_id，失败返回 None"""
    key = str(name).rstrip("*").strip()
    if not key:
        return None
    if key in mapping:
        return mapping[key]
    words = key.split()
    if len(words) >= 2 and " ".join(words[-2:]) in mapping:
        return mapping[" ".join(words[-2:])]
    if words and words[-1] in mapping:
        return mapping[words[-1]]
    return None


def season_has_data(season: str) -> bool:
    with SessionLocal() as db:
        return db.query(PlayerData).filter(PlayerData.season == season).count() > 0


def save_player_season(df: pd.DataFrame, season: str, force: bool = False):
    """写入 PlayerData + PlayerRoster（不含 TOT 汇总行）"""
    if not force and season_has_data(season):
        logger.info(f"  [{season}] 已有球员数据，跳过（--force 可覆盖）")
        return

    with SessionLocal() as db:
        name_map = load_players(db)
        abbr_map = team_abbr_map(db)
        known_slugs = {p.nba_id for p in db.query(Player.nba_id).all()}

        added_players = 0
        pd_rows = 0
        roster_rows = 0
        skipped_tot = 0

        def get_or_create_player(row, nkey) -> Player:
            nonlocal added_players
            player = name_map.get(nkey)
            if player is None:
                slug = str(row.get("_slug", ""))
                nba_id = f"bbref_{slug}" if slug else fallback_nba_id(nkey)
                if nba_id in known_slugs:
                    player = db.query(Player).filter(Player.nba_id == nba_id).first()
                if player is None:
                    team_id = abbr_map.get(str(row.get("Tm", "")))
                    player = Player(
                        nba_id=nba_id,
                        player_name=str(row.get("Player", "")),
                        player_name_en=str(row.get("Player", "")),
                        team_id=team_id,
                        position=str(row.get("Pos", "")) if row.get("Pos") else None,
                        status=1,
                    )
                    db.add(player)
                    db.flush()
                    added_players += 1
                    name_map[nkey] = player
                    known_slugs.add(nba_id)
            elif not player.nba_id:
                slug = str(row.get("_slug", ""))
                if slug:
                    player.nba_id = f"bbref_{slug}"
            # 已有球员也回填空缺的位置（旧数据 position 曾为假值被清空）
            if player is not None and not player.position:
                pos = row.get("Pos")
                if pos and str(pos) not in ("nan", "None"):
                    player.position = str(pos)
            return player

        def build_pd_row(player, row, team_id) -> PlayerData:
            return PlayerData(
                player_id=player.player_id,
                season=season,
                team_id=team_id,
                games_played=int(num(row.get("G"))),
                games_started=int_or_null(row.get("GS")),
                minutes_per_game=num(row.get("MP")),
                points_per_game=num(row.get("PTS")),
                rebounds_per_game=num(row.get("TRB")),
                assists_per_game=num(row.get("AST")),
                steals_per_game=num(row.get("STL")),
                blocks_per_game=num(row.get("BLK")),
                turnovers_per_game=num(row.get("TOV")),
                fg_made_per_game=num(row.get("FG")),
                fg_attempted_per_game=num(row.get("FGA")),
                fg_percentage=num(row.get("FG%")),
                three_made_per_game=num(row.get("3P")),
                three_attempted_per_game=num(row.get("3PA")),
                three_percentage=num(row.get("3P%")),
                ft_made_per_game=num(row.get("FT")),
                ft_attempted_per_game=num(row.get("FTA")),
                ft_percentage=num(row.get("FT%")),
                per=num(row.get("PER")),
                true_shooting_pct=num(row.get("TS%")),
                usage_rate=num(row.get("USG%")),
                win_shares=num(row.get("WS")),
                bpm=num(row.get("BPM")),
                vorp=num(row.get("VORP")),
                isolation_pct=None,
                pick_roll_pct=None,
                spot_up_pct=None,
                post_up_pct=None,
                points_std=None,
                points_cv=None,
                offensive_rating=num(row.get("ORtg")),
                defensive_rating=num(row.get("DRtg")),
                assist_pct=num(row.get("AST%")),
                rebound_pct=num(row.get("TRB%")),
                steal_pct=num(row.get("STL%")),
                block_pct=num(row.get("BLK%")),
                turnover_pct=num(row.get("TOV%")),
                effective_fg_pct=num(row.get("eFG%")),
            )

        # 按球员分组：库内 player_data 唯一键是 (player_id, season)，
        # 多队球员用 TOT 汇总行，名单仍保留每个队的行
        grouped = df.groupby("_norm", sort=False)
        for nkey, grp in grouped:
            rows = grp.to_dict("records")
            partial = [r for r in rows if str(r.get("Tm", "")) != "TOT"]
            tot = [r for r in rows if str(r.get("Tm", "")) == "TOT"]
            skipped_tot += len(tot)
            if not partial:
                continue

            player = get_or_create_player(partial[0], nkey)

            # PlayerData: TOT 优先，否则第一支队的行
            stat_row = tot[0] if tot else partial[0]
            if tot:
                # TOT 行无具体队：用球员当前球队或第一支队
                team_id = player.team_id or abbr_map.get(str(partial[0].get("Tm", "")))
            else:
                team_id = abbr_map.get(str(stat_row.get("Tm", "")))
            if not team_id:
                continue
            db.query(PlayerData).filter(
                PlayerData.player_id == player.player_id,
                PlayerData.season == season,
            ).delete()
            db.add(build_pd_row(player, stat_row, team_id))
            pd_rows += 1

            # PlayerRoster: 每支队一行（含被交易前的队）；分段表可能有重复行，按 key 去重
            seen_roster_keys = set()
            for r in partial:
                team_id_r = abbr_map.get(str(r.get("Tm", "")))
                if not team_id_r:
                    continue
                rkey = (player.player_id, team_id_r, season)
                if rkey in seen_roster_keys:
                    continue
                seen_roster_keys.add(rkey)
                gp = int(num(r.get("G")))
                pos = str(r.get("Pos", "")) if r.get("Pos") else None
                existing = db.query(PlayerRoster).filter(
                    PlayerRoster.player_id == player.player_id,
                    PlayerRoster.team_id == team_id_r,
                    PlayerRoster.season == season,
                ).first()
                if existing:
                    existing.position = pos
                    existing.games_played = gp
                    existing.age = int_or_null(r.get("Age"))
                else:
                    db.add(PlayerRoster(
                        player_id=player.player_id,
                        team_id=team_id_r,
                        season=season,
                        position=pos,
                        games_played=gp,
                        age=int_or_null(r.get("Age")),
                    ))
                    roster_rows += 1

        db.commit()
        logger.info(
            f"  [{season}] 新增球员 {added_players}, PlayerData {pd_rows}, "
            f"名单 {roster_rows}, 跳过TOT {skipped_tot}"
        )


def fetch_team_season(season: str, force: bool = False):
    """某赛季球队数据 -> TeamData（战绩 + 高阶；缺失行会创建）"""
    year = BBREF_YEAR[season]
    url = f"{BASE}/leagues/NBA_{year}.html"
    html = curl_fetch(url)
    if not html:
        logger.error(f"  [{season}] 球队数据页抓取失败")
        return
    tables = [flat(t) for t in pd.read_html(StringIO(html))]
    standings_matches = [
        t for t in tables
        if "W" in list(t.columns) and "L" in list(t.columns) and "PS/G" in list(t.columns)
    ]
    misc_matches = [t for t in tables if "Pace" in list(t.columns) and "ORtg" in list(t.columns)]
    delay()
    if not standings_matches:
        logger.error(f"  [{season}] 未找到战绩表")
        return
    misc = pd.concat(misc_matches, ignore_index=True) if misc_matches else pd.DataFrame()

    with SessionLocal() as db:
        abbr_map = team_abbr_map(db)
        existing_map = {
            td.team_id: td
            for td in db.query(TeamData).filter(TeamData.season == season).all()
        }
        if existing_map and not force:
            logger.info(f"  [{season}] 已有球队数据，跳过")
            return

        # 东西两个战绩表第一列名不同（分区名作表头），必须逐表处理避免 concat 列错位
        created = updated = 0
        for standings in standings_matches:
            abbr_col = list(standings.columns)[0]
            for _, row in standings.iterrows():
                team_id = team_id_of(abbr_map, row.get(abbr_col, ""))
                if not team_id:
                    continue
                td = existing_map.get(team_id)
                if td is None:
                    td = TeamData(team_id=team_id, season=season)
                    db.add(td)
                    existing_map[team_id] = td
                    created += 1
                td.wins = int_or_null(row.get("W")) or 0
                td.losses = int_or_null(row.get("L")) or 0
                td.win_percentage = num(row.get("W-L%"))
                td.points_per_game = num(row.get("PS/G"))
                td.opponent_points = num(row.get("PA/G"))
                updated += 1

        # 高阶表: Pace / ORtg / DRtg / NRtg
        if not misc.empty:
            for _, row in misc.iterrows():
                team_id = team_id_of(abbr_map, row.get("Tm", ""))
                if not team_id or team_id not in existing_map:
                    continue
                td = existing_map[team_id]
                td.pace = num(row.get("Pace"))
                td.offensive_rating = num(row.get("ORtg"))
                td.defensive_rating = num(row.get("DRtg"))
                td.net_rating = num(row.get("NRtg"))
        db.commit()
        logger.info(f"  [{season}] 球队数据: 新建 {created}, 更新 {updated} 队")


def backfill_player_bio(current_season: str = "2025-26"):
    """用现役名单页回填 Player 的 height/weight/birth_date/jersey_number"""
    year = BBREF_YEAR[current_season]
    with SessionLocal() as db:
        abbr_map = team_abbr_map(db)
        name_map = load_players(db)
        teams = db.query(Team).all()

    updated = 0
    for t in teams:
        if t.abbreviation not in abbr_map:
            continue
        url = f"{BASE}/teams/{t.abbreviation}/{year}.html"
        html = curl_fetch(url)
        if not html:
            continue
        try:
            tables = [flat(tb) for tb in pd.read_html(StringIO(html))]
        except ValueError:
            logger.warning(f"  名单页解析失败: {t.abbreviation}")
            delay()
            continue
        roster = [tb for tb in tables if "Player" in list(tb.columns) and "Ht" in list(tb.columns)]
        delay()
        if not roster:
            continue
        roster = pd.concat(roster, ignore_index=True)
        with SessionLocal() as db:
            for _, row in roster.iterrows():
                name = str(row.get("Player", ""))
                player = db.query(Player).filter(Player.player_id == name_map.get(norm_name(name), -1).player_id).first() \
                    if norm_name(name) in name_map else None
                if player is None:
                    continue
                if not player.height and row.get("Ht"):
                    player.height = cm_from_bbref(str(row["Ht"]))
                if not player.weight and row.get("Wt"):
                    player.weight = kg_from_lbs(row["Wt"])
                if not player.birth_date and row.get("Birth Date"):
                    try:
                        player.birth_date = datetime.strptime(str(row["Birth Date"]), "%B %d, %Y").date()
                    except ValueError:
                        pass
                if not player.jersey_number and row.get("#"):
                    player.jersey_number = int_or_null(row.get("#"))
                updated += 1
            db.commit()
    logger.info(f"球员资料回填: 更新 {updated} 条")


def run(seasons=None, force=False, skip_bio=False):
    seasons = seasons or SEASONS_10
    logger.info("=" * 60)
    logger.info("bbref 10 赛季数据采集开始")
    logger.info("=" * 60)

    for season in seasons:
        logger.info(f"\n[{season}] 抓取球员数据...")
        df, _ = fetch_player_pages(season)
        if df is not None:
            save_player_season(df, season, force=force)
        fetch_team_season(season, force=force)

    if not skip_bio:
        logger.info("\n回填球员资料（身高/体重/生日/球衣号）...")
        backfill_player_bio()

    logger.info("\n" + "=" * 60)
    logger.info("bbref 采集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", default=None, help="逗号分隔赛季，如 2016-17,2017-18")
    parser.add_argument("--force", action="store_true", help="覆盖已有赛季数据")
    parser.add_argument("--skip-bio", action="store_true", help="跳过球员资料回填")
    args = parser.parse_args()

    run(
        seasons=args.seasons.split(",") if args.seasons else None,
        force=args.force,
        skip_bio=args.skip_bio,
    )
