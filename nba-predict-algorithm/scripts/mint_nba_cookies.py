"""
从 www.nba.com 获取 Akamai 会话 cookie（_abck 等），供 stats.nba.com 请求使用

stats.nba.com 对无有效会话的请求返回 "We are unable to process your request"
错误页。Akamai 的 _abck cookie 只能通过真实浏览器执行 JS 校验获得。
本脚本用 Playwright 有头浏览器（真实窗口，短暂弹出）访问 nba.com 完成校验，
导出 cookie 到 data/nba_session_cookies.json。cookie 有效数小时，爬取脚本
检测到封禁时会自动重新获取。

用法:
    python scripts/mint_nba_cookies.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from playwright.sync_api import sync_playwright

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COOKIE_FILE = DATA_DIR / "nba_session_cookies.json"

# 经本机 Clash 代理访问（出口 IP 需与后续 API 请求一致）
PROXY = {"server": "http://127.0.0.1:7897"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

PAGES = [
    "https://www.nba.com/",
    "https://www.nba.com/stats",
    "https://www.nba.com/news",
]


def mint_cookies() -> dict:
    """启动有头浏览器访问 nba.com，等待 Akamai 校验完成，返回 cookie dict"""
    with sync_playwright() as p:
        # headless=False: 真实浏览器窗口，Akamai 对无头浏览器的检测更严格
        browser = p.chromium.launch(headless=False, proxy=PROXY, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = ctx.new_page()

        for url in PAGES:
            try:
                logger.info(f"访问 {url} ...")
                resp = page.goto(url, wait_until="domcontentloaded", timeout=90000)
                logger.info(f"  状态 {resp.status if resp else 'N/A'}, 标题: {page.title()[:60]}")
                # 等 Akamai sensor JS 执行并回写 _abck
                page.wait_for_timeout(10000)
            except Exception as e:
                logger.warning(f"  访问失败: {e}")

        cookies = ctx.cookies()
        browser.close()

    cookie_map = {c["name"]: c["value"] for c in cookies}
    DATA_DIR.mkdir(exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(cookie_map, indent=2, ensure_ascii=False))

    logger.info(f"获取 {len(cookie_map)} 个 cookie: {list(cookie_map.keys())}")
    if not cookie_map:
        logger.error("未获取到任何 cookie，Akamai 校验可能未通过")
    return cookie_map


def load_cookies() -> dict:
    """读取已保存的 cookie，文件不存在则返回空 dict"""
    if not COOKIE_FILE.exists():
        return {}
    return json.loads(COOKIE_FILE.read_text())


if __name__ == "__main__":
    mint_cookies()
