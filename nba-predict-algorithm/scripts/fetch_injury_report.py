"""
伤病报告抓取脚本
从 ESPN 公开 API 获取 NBA 伤病数据，更新到 Player 表
ESPN API: https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries
"""
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, date
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player

ESPN_INJURY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"

# ESPN 伤病状态 → 系统状态映射
STATUS_MAP = {
    "Out": "INJURED",
    "Out For Season": "INJURED",
    "Out For Season (Rest)": "INJURED",
    "Doubtful": "RECOVERY",
    "Questionable": "RECOVERY",
    "Probable": "RECOVERY",
    "Day-To-Day": "RECOVERY",
    "Available": "HEALTHY",
    "Healthy": "HEALTHY",
}


def _similar(a: str, b: str) -> float:
    """计算两个名字的相似度"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fetch_espn_injuries() -> list:
    """从 ESPN API 抓取伤病报告"""
    try:
        resp = requests.get(ESPN_INJURY_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"ESPN 伤病 API 请求失败: {e}")
        return []

    injuries = []
    # ESPN 返回格式: {"items": [{"team": {...}, "injuries": [...]}]}
    items = data.get("items", [])
    if not items:
        # 备用格式: {"children": [{"team": {...}, "injuries": [...]}]}
        items = data.get("children", [])

    for team_block in items:
        team_info = team_block.get("team", {})
        team_name = team_info.get("displayName", "")
        team_abbr = team_info.get("abbreviation", "")

        injury_list = team_block.get("injuries", [])
        for inj in injury_list:
            athlete = inj.get("athlete", {})
            details = inj.get("details", {})
            status_text = inj.get("status", "")

            player_name = athlete.get("fullName", athlete.get("displayName", ""))
            injury_desc = details.get("detail", details.get("type", {}).get("description", ""))

            # 归一化状态
            system_status = STATUS_MAP.get(status_text, "RECOVERY")

            injuries.append({
                "player_name": player_name,
                "team_abbr": team_abbr,
                "team_name": team_name,
                "status_raw": status_text,
                "status": system_status,
                "injury_desc": injury_desc,
            })

    logger.info(f"ESPN 伤病报告: 共 {len(injuries)} 条记录")
    return injuries


def update_injuries(injuries: list):
    """将伤病数据更新到 Player 表"""
    if not injuries:
        logger.warning("无伤病数据可更新")
        return

    with SessionLocal() as db:
        # 获取所有活跃球员
        players = db.query(Player).filter(Player.status == 1).all()

        # 构建名字索引 (name → player)
        name_index = {}
        for p in players:
            if p.player_name:
                name_index[p.player_name] = p
            if p.player_name_en:
                name_index[p.player_name_en] = p

        matched = 0
        updated_injured = 0
        updated_healthy = 0
        unmatched = []

        # 记录已匹配的球员 ID
        matched_ids = set()

        for inj in injuries:
            pname = inj["player_name"]
            if not pname:
                continue

            # 精确匹配
            player = name_index.get(pname)

            # 模糊匹配 (处理 Jr./Sr./II/III 等后缀差异)
            if not player:
                best_score = 0
                best_player = None
                for p in players:
                    for name in [p.player_name, p.player_name_en]:
                        if not name:
                            continue
                        score = _similar(pname, name)
                        if score > best_score and score > 0.80:
                            best_score = score
                            best_player = p
                player = best_player

            if player:
                matched_ids.add(player.player_id)
                player.injury_status = inj["status"]
                player.injury_type = inj["injury_desc"][:100] if inj["injury_desc"] else None
                player.injury_date = date.today()
                matched += 1
                if inj["status"] == "INJURED":
                    updated_injured += 1
                elif inj["status"] == "RECOVERY":
                    updated_healthy += 1  # RECOVERY 也算"有伤"
            else:
                unmatched.append(f"{pname} ({inj['team_abbr']})")

        # 未在伤病报告中的球员 → HEALTHY
        for p in players:
            if p.player_id not in matched_ids and p.injury_status != "HEALTHY":
                p.injury_status = "HEALTHY"
                p.injury_type = None
                p.injury_date = date.today()
                updated_healthy += 1

        db.commit()

        logger.info(f"伤病更新完成: 匹配 {matched}/{len(injuries)}")
        logger.info(f"  受伤/缺阵: {updated_injured}")
        logger.info(f"  恢复健康: {updated_healthy}")

        if unmatched:
            logger.warning(f"未匹配球员 ({len(unmatched)}):")
            for name in unmatched[:10]:
                logger.warning(f"  - {name}")
            if len(unmatched) > 10:
                logger.warning(f"  ... 还有 {len(unmatched) - 10} 人")


def run():
    """主入口"""
    logger.info("=" * 50)
    logger.info(f"伤病报告更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 50)

    injuries = fetch_espn_injuries()
    update_injuries(injuries)

    logger.info("伤病报告更新完成")


if __name__ == "__main__":
    run()
