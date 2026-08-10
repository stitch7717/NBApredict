"""
修复球员名称不匹配问题：
将数据库中的缩写名更新为 ESPN 全名，并重新聚合缺失数据
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData
from sqlalchemy import text

ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            return None


def get_espn_names_from_game(espn_game_id):
    """从一场比赛获取所有 ESPN 球员名"""
    url = f"{ESPN_SUMMARY}?event={espn_game_id}"
    data = fetch_json(url)
    if not data or "boxscore" not in data:
        return set()

    names = set()
    for team in data["boxscore"].get("players", []):
        for stat_group in team.get("statistics", []):
            for athlete in stat_group.get("athletes", []):
                name = athlete.get("athlete", {}).get("displayName", "")
                if name:
                    names.add(name)
    return names


def build_name_mapping():
    """构建 ESPN 名 -> DB 名 的映射"""
    db = SessionLocal()
    try:
        # 获取所有 DB 球员名
        result = db.execute(text("SELECT player_id, player_name FROM player"))
        db_players = {row[1]: row[0] for row in result}

        # 从缓存获取 ESPN 球员名
        cache_file = Path(__file__).resolve().parent.parent / "data" / "espn_cache" / "boxscore_cache.json"
        if not cache_file.exists():
            logger.error("缓存文件不存在")
            return {}

        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)

        # 从缓存中提取所有 ESPN 球员名
        espn_names = set()
        for game_id, boxscore in list(cache.items())[:100]:  # 只检查前100场
            if not isinstance(boxscore, list):
                continue
            for team in boxscore:
                for p in team.get("players", []):
                    name = p.get("name", "")
                    if name:
                        espn_names.add(name)

        logger.info(f"DB 球员: {len(db_players)}, ESPN 球员样本: {len(espn_names)}")

        # 构建映射：尝试匹配
        mapping = {}  # espn_name -> db_player_name

        for espn_name in espn_names:
            if espn_name in db_players:
                continue  # 已匹配

            espn_parts = espn_name.split()
            if len(espn_parts) < 2:
                continue

            espn_first = espn_parts[0]
            espn_last = " ".join(espn_parts[1:])

            # 尝试匹配：DB 中的缩写名
            for db_name, db_pid in db_players.items():
                db_parts = db_name.split()
                if len(db_parts) < 2:
                    continue

                db_first = db_parts[0]
                db_last = " ".join(db_parts[1:])

                # 姓必须匹配
                if db_last.lower() != espn_last.lower():
                    continue

                # 名可能是缩写
                if db_first.lower() == espn_first.lower():
                    continue  # 完全匹配，跳过

                # 检查是否是缩写（如 Lu -> Luguentz, PJ -> P.J.）
                if espn_first.lower().startswith(db_first.lower()) or db_first.lower().startswith(espn_first.lower()):
                    mapping[espn_name] = db_name
                    break

                # 检查带点的缩写（如 P.J. -> PJ）
                espn_clean = espn_first.replace(".", "").replace("'", "").lower()
                db_clean = db_first.replace(".", "").replace("'", "").lower()
                if espn_clean == db_clean:
                    mapping[espn_name] = db_name
                    break

        return mapping
    finally:
        db.close()


def fix_names_and_reaggregate():
    """修复名称并重新聚合数据"""
    logger.info("=" * 60)
    logger.info("修复球员名称不匹配问题")
    logger.info("=" * 60)

    # 构建映射
    mapping = build_name_mapping()
    logger.info(f"找到 {len(mapping)} 个名称映射:")
    for espn, db in mapping.items():
        logger.info(f"  {espn} -> {db}")

    if not mapping:
        logger.info("没有需要修复的映射")
        return

    db = SessionLocal()
    try:
        # 更新数据库中的球员名
        for espn_name, db_name in mapping.items():
            result = db.execute(text("""
                SELECT player_id FROM player WHERE player_name = :name
            """), {"name": db_name})
            row = result.fetchone()
            if row:
                # 更新为 ESPN 全名
                db.execute(text("""
                    UPDATE player SET player_name = :espn_name WHERE player_id = :pid
                """), {"espn_name": espn_name, "pid": row[0]})
                logger.info(f"  更新: {db_name} -> {espn_name}")

        db.commit()
        logger.info("名称更新完成")

        # 验证
        result = db.execute(text("SELECT COUNT(DISTINCT player_name) FROM player"))
        logger.info(f"唯一球员名: {result.scalar()}")

    finally:
        db.close()


if __name__ == "__main__":
    fix_names_and_reaggregate()
