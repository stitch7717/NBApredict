"""
测试 nba_api 可用性 - 自定义请求头 + 反爬策略
"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

# 自定义请求头 (模拟浏览器)
CUSTOM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# nba_api 使用的静态头部
NBA_API_STATIC_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


def test_direct_request():
    """直接测试 stats.nba.com API"""
    import urllib.request
    import ssl

    logger.info("[测试] 直接请求 stats.nba.com...")

    url = "https://stats.nba.com/stats/leaguedashplayerstats?College=&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick=&DraftYear=&GameScope=&GameSegment=&Height=&ISTRound=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2024-25&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight="

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers=NBA_API_STATIC_HEADERS)
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        data = json.loads(resp.read())
        headers = data.get("resultSets", [{}])[0].get("headers", [])
        rows = data.get("resultSets", [{}])[0].get("rowSet", [])
        logger.info(f"  成功! 获取 {len(rows)} 名球员")
        logger.info(f"  响应头字段数: {len(headers)}")
        if rows:
            logger.info(f"  示例: {rows[0][1]} - {rows[0][26]}pts")
        return True
    except Exception as e:
        logger.error(f"  失败: {type(e).__name__}: {e}")
        return False


def test_nba_api_with_proxy():
    """测试 nba_api 通过代理"""
    logger.info("[测试] nba_api 通过代理...")
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
        from nba_api.stats.library.http import NBAStatsHTTP

        # 尝试修改默认 headers
        original_send = NBAStatsHTTP.send_nba_request

        def custom_send(self, *args, **kwargs):
            # 注入自定义 headers
            if hasattr(self, '_headers'):
                self._headers.update(NBA_API_STATIC_HEADERS)
            return original_send(self, *args, **kwargs)

        NBAStatsHTTP.send_nba_request = custom_send

        data = leaguedashplayerstats.LeagueDashPlayerStats(
            season="2024-25",
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            timeout=30,
        )
        df = data.get_data_frames()[0]
        logger.info(f"  成功! 获取 {len(df)} 名球员")
        return True
    except Exception as e:
        logger.error(f"  失败: {type(e).__name__}: {e}")
        return False


def test_raw_stats_api():
    """直接用 requests 测试 stats.nba.com"""
    logger.info("[测试] requests 直接请求 stats.nba.com...")
    try:
        import requests

        url = "https://stats.nba.com/stats/leaguedashplayerstats"
        params = {
            "College": "", "Conference": "", "Country": "",
            "DateFrom": "", "DateTo": "", "Division": "",
            "DraftPick": "", "DraftYear": "", "GameScope": "",
            "GameSegment": "", "Height": "", "ISTRound": "",
            "LastNGames": "0", "LeagueID": "00", "Location": "",
            "MeasureType": "Base", "Month": "0", "OpponentTeamID": "0",
            "Outcome": "", "PORound": "0", "PaceAdjust": "N",
            "PerMode": "PerGame", "Period": "0", "PlayerExperience": "",
            "PlayerPosition": "", "PlusMinus": "N", "Rank": "N",
            "Season": "2024-25", "SeasonSegment": "",
            "SeasonType": "Regular Season", "ShotClockRange": "",
            "StarterBench": "", "TeamID": "0", "VsConference": "",
            "VsDivision": "",
        }

        resp = requests.get(url, params=params, headers=NBA_API_STATIC_HEADERS, timeout=30)
        logger.info(f"  状态码: {resp.status_code}")
        logger.info(f"  响应长度: {len(resp.text)} 字符")

        if resp.status_code == 200:
            data = resp.json()
            rows = data.get("resultSets", [{}])[0].get("rowSet", [])
            logger.info(f"  成功! 获取 {len(rows)} 名球员")
            return True
        else:
            logger.error(f"  响应内容: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"  失败: {type(e).__name__}: {e}")
        return False


def test_espn_api():
    """测试 ESPN API（备用方案）"""
    logger.info("[测试] ESPN API...")
    try:
        import urllib.request
        import ssl

        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20250101&limit=10"
        headers = {"User-Agent": "Mozilla/5.0"}

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())
        events = data.get("events", [])
        logger.info(f"  成功! 获取 {len(events)} 场比赛")
        if events:
            logger.info(f"  示例: {events[0].get('name', 'N/A')}")
        return True
    except Exception as e:
        logger.error(f"  失败: {type(e).__name__}: {e}")
        return False


def run():
    logger.info("=" * 60)
    logger.info("数据源可用性测试")
    logger.info("=" * 60)

    results = {}

    tests = [
        ("ESPN API", test_espn_api),
        ("stats.nba.com 直接请求", test_raw_stats_api),
        ("stats.nba.com urllib", test_direct_request),
    ]

    for name, func in tests:
        time.sleep(2)
        results[name] = func()

    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总:")
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        logger.info(f"  {name}: {status}")

    passed = sum(1 for v in results.values() if v)
    logger.info(f"\n通过: {passed}/{len(results)}")
    logger.info("=" * 60)

    return any(results.values())


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
