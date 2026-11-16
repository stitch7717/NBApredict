"""
从 basketball-reference 采集球队分距离投篮命中数据（Shooting 表）

数据源页面: /teams/{TLA}/{year}.html（每队 1 页，共 30 页）
分区: at_rim(篮下) / 3_10 / 10_16 / 16_3p(长两分) / 3p(三分)

注意（与 fetch_bbref_seasons.py 相同约束）:
- 必须用 curl 子进程 + Clash 代理（TLS 指纹检测，requests 会被 403）
- 每请求间隔 >= 7s；Cloudflare 质询页指数退避
- 抓取后做数量断言: 30 队 × 5 区 = 150 行，缺失会显式报错

用法: python scripts/fetch_team_shooting.py [season]  （默认 2025-26）
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import Team, TeamShootingZone

PROXY = "http://127.0.0.1:7897"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_DELAY = 7.0
BASE = "https://www.basketball-reference.com"

# bbref 距离标签（新旧两种叫法）→ 内部 zone key
ZONE_ALIASES = [
    (r"at rim|0-3(?: ft)?", "at_rim"),
    (r"3 to <10|3-10(?: ft)?", "3_10"),
    (r"10 to <16|10-16(?: ft)?", "10_16"),
    (r"16 ft to <3-pt|16-3p", "16_3p"),
    (r"3-pt|3p", "3p"),
]

EXPECTED_ZONES = ["at_rim", "3_10", "10_16", "16_3p", "3p"]


def curl_fetch(url: str, retries: int = 5) -> str:
    """curl 子进程抓取；Cloudflare 质询页出现时指数退避重试"""
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "-s", "-x", PROXY, "-A", USER_AGENT, "--max-time", "60", url],
            capture_output=True, text=True, timeout=90,
        )
        html = r.stdout or ""
        if "Just a moment" in html or "cf-challenge" in html.lower():
            wait = 30 * (2 ** attempt)
            logger.warning(f"Cloudflare 质询页，{wait}s 后重试 ({attempt + 1}/{retries})")
            time.sleep(wait)
            continue
        if len(html) < 5000:
            logger.warning(f"页面过小({len(html)}B)，可能被拦截，重试 ({attempt + 1}/{retries})")
            time.sleep(REQUEST_DELAY)
            continue
        return html
    return ""


def normalize_zone(label: str):
    """距离标签 → 内部 zone key，无法识别返回 None"""
    for pattern, key in ZONE_ALIASES:
        if re.search(pattern, label, re.IGNORECASE):
            return key
    return None


def parse_shooting_table(html: str):
    """解析 Shooting 表，返回 {zone_key: (fg_made, fg_attempted, fg_pct)}"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="shooting")
    if table is None:
        return None

    # 表头 → 列名（bbref 列名带注释会拼成 "FieldName"，用 data-stat 更稳）
    headers = {}
    for th in table.find("thead").find_all("th"):
        stat = th.get("data-stat", "")
        headers[th] = stat

    rows = table.find("tbody").find_all("tr")
    result = {}
    for tr in rows:
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        zone = normalize_zone(label)
        if zone is None:
            continue
        values = {}
        for cell, stat in zip(cells[1:], [c.get("data-stat", "") for c in cells[1:]]):
            values[stat] = cell.get_text(strip=True)
        try:
            fg = int(re.sub(r"[^0-9]", "", values.get("fg", "0")) or 0)
            fga = int(re.sub(r"[^0-9]", "", values.get("fga", "0")) or 0)
            if fga == 0:  # 个别赛季列名不同，用 2P+3P 合计兜底
                fg = int(re.sub(r"[^0-9]", "", values.get("fg2", "0")) or 0) + \
                     int(re.sub(r"[^0-9]", "", values.get("fg3", "0")) or 0)
                fga = int(re.sub(r"[^0-9]", "", values.get("fga2", "0")) or 0) + \
                      int(re.sub(r"[^0-9]", "", values.get("fga3", "0")) or 0)
            pct_text = values.get("fg_pct", "")
            pct = float(re.sub(r"[^0-9.]", "", pct_text) or 0) / 100 if "%" in pct_text else float(pct_text or 0)
        except (ValueError, KeyError):
            logger.warning(f"行解析失败: {label}")
            continue
        result[zone] = (fg, fga, pct)
    return result


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "2025-26"
    year = season[:2] + season[5:7]  # "2025-26" -> "2026"

    with SessionLocal() as db:
        teams = db.query(Team).filter(Team.status == 1).order_by(Team.team_id).all()
    logger.info(f"目标: {len(teams)} 支球队, {season} 赛季 (bbref 年份 {year})")

    inserted = 0
    failures = []
    with SessionLocal() as db:
        for i, team in enumerate(teams):
            abbr = team.abbreviation
            url = f"{BASE}/teams/{abbr}/{year}.html"
            html = curl_fetch(url)
            zones = parse_shooting_table(html) if html else None
            if not zones or len(zones) < len(EXPECTED_ZONES):
                failures.append(abbr)
                logger.error(f"{abbr}: 抓取/解析失败 (zones={list(zones.keys()) if zones else None})")
            else:
                for key in EXPECTED_ZONES:
                    made, att, pct = zones[key]
                    row = db.query(TeamShootingZone).filter_by(
                        team_id=team.team_id, season=season, zone=key,
                    ).first()
                    if row is None:
                        row = TeamShootingZone(team_id=team.team_id, season=season, zone=key)
                        db.add(row)
                    row.fg_made = made
                    row.fg_attempted = att
                    row.fg_percentage = pct
                inserted += len(EXPECTED_ZONES)
                logger.info(f"{abbr}: 5 区入库 OK (篮下 {zones['at_rim'][2]:.1%})")
            time.sleep(REQUEST_DELAY)
        db.commit()

    # 数量断言：30 队 × 5 区 = 150 行（失败显式报错，不静默）
    with SessionLocal() as db:
        total = db.query(TeamShootingZone).filter_by(season=season).count()
    expected = len(teams) * len(EXPECTED_ZONES)
    logger.info(f"完成: 插入/更新 {inserted} 行, 库中该赛季共 {total} 行 (预期 {expected})")
    if failures:
        logger.error(f"失败球队({len(failures)}): {failures} — 请重跑或检查代理")
        sys.exit(1)
    if total < expected:
        logger.error(f"数量断言失败: {total} < {expected}")
        sys.exit(1)
    logger.info("数量断言通过")


if __name__ == "__main__":
    main()
