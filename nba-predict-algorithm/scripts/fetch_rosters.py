"""
从 ESPN API 抓取全部 NBA 球队阵容和球员基础数据
"""
import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, Team

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"

# 内部 team_id -> ESPN abbreviation（注意 ESPN 用的是缩写不同）
TEAM_ABBR_MAP = {
    1: "ATL", 2: "BOS", 3: "BKN", 4: "CHA", 5: "CHI",
    6: "CLE", 7: "DET", 8: "IND", 9: "MIA", 10: "MIL",
    11: "NY",   # ESPN 用 NY 不是 NYK
    12: "ORL", 13: "PHI", 14: "TOR",
    15: "WSH",  # ESPN 用 WSH 不是 WAS
    16: "DAL", 17: "DEN",
    18: "GS",   # ESPN 用 GS 不是 GSW
    19: "HOU", 20: "LAC", 21: "LAL", 22: "MEM", 23: "MIN",
    24: "NO",   # ESPN 用 NO 不是 NOP
    25: "OKC", 26: "PHX", 27: "POR", 28: "SAC",
    29: "SA",   # ESPN 用 SA 不是 SAS
    30: "UTAH", # ESPN 用 UTAH 不是 UTA
}

# 位置映射
POS_MAP = {
    "Guard": "PG", "Point Guard": "PG", "Shooting Guard": "SG",
    "Forward": "SF", "Small Forward": "SF", "Power Forward": "PF",
    "Center": "C", "G": "PG", "F": "SF", "C": "C",
}


def fetch_roster(abbr: str) -> list:
    """获取某队阵容"""
    url = ESPN_ROSTER_URL.format(abbr)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get("athletes", [])
    except Exception as e:
        logger.warning(f"获取 {abbr} 阵容失败: {e}")
        return []


def parse_height(h) -> float:
    """ESPN height (inches) -> cm"""
    if not h:
        return 0
    return round(h * 2.54, 1)


def parse_weight(w) -> float:
    """ESPN weight (lbs) -> kg"""
    if not w:
        return 0
    return round(w * 0.4536, 1)


def parse_pos(pos_dict: dict) -> str:
    """解析位置"""
    if not pos_dict:
        return ""
    abbr = pos_dict.get("abbreviation", "")
    return POS_MAP.get(abbr, abbr)


def run():
    logger.info("=" * 50)
    logger.info("从 ESPN 抓取全部 NBA 球队阵容")
    logger.info("=" * 50)

    with SessionLocal() as db:
        existing_players = {p.nba_id: p for p in db.query(Player).all()}
        logger.info(f"数据库已有 {len(existing_players)} 名球员")

        total_added = 0
        total_updated = 0

        for team_id, abbr in TEAM_ABBR_MAP.items():
            logger.info(f"抓取 {abbr} (team_id={team_id})...")
            athletes = fetch_roster(abbr)
            if not athletes:
                continue

            added = 0
            updated = 0
            for ath in athletes:
                espn_id = str(ath.get("id", ""))
                if not espn_id:
                    continue

                name = ath.get("displayName", "")
                first = ath.get("firstName", "")
                last = ath.get("lastName", "")
                pos = parse_pos(ath.get("position"))
                jersey = ath.get("jersey")
                if jersey:
                    try:
                        jersey = int(jersey)
                    except:
                        jersey = None
                age = ath.get("age")
                height = parse_height(ath.get("height"))
                weight = parse_weight(ath.get("weight"))
                debut = ath.get("debutYear")

                if espn_id in existing_players:
                    # 更新已有球员
                    p = existing_players[espn_id]
                    if p.team_id != team_id:
                        p.team_id = team_id
                        updated += 1
                    if pos and p.position != pos:
                        p.position = pos
                    if name and p.player_name != name:
                        p.player_name = name
                else:
                    # 新增球员
                    player = Player(
                        nba_id=espn_id,
                        player_name=name,
                        player_name_en=name,
                        position=pos,
                        jersey_number=jersey,
                        team_id=team_id,
                        age=age,
                        height=height,
                        weight=weight,
                        experience=2025 - debut if debut else None,
                        all_star_count=0,
                        all_star_last=0,
                        injury_status="健康",
                        player_type="普通球员",
                        status=1,
                    )
                    db.add(player)
                    added += 1

            db.commit()
            logger.info(f"  {abbr}: 新增 {added}, 更新 {updated}")
            total_added += added
            total_updated += updated

        logger.info("=" * 50)
        logger.info(f"完成: 新增 {total_added}, 更新 {total_updated}")

        # 统计
        total = db.query(Player).count()
        logger.info(f"数据库球员总数: {total}")

        # 按球队统计
        from collections import Counter
        players = db.query(Player).all()
        team_counts = Counter(p.team_id for p in players)
        logger.info(f"每队平均: {total / 30:.1f} 名球员")


if __name__ == "__main__":
    run()
