"""
NBA预测系统 - 算法层入口
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import API_HOST, API_PORT
from app.api import player, team, odds, series, config, data
from app.core.exceptions import register_exception_handlers
from app.core.logger import setup_logger

# 初始化日志
logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("NBA预测算法层启动中...")
    _check_data_freshness()
    yield
    logger.info("NBA预测算法层关闭")


def _check_data_freshness():
    """启动时检查数据是否已更新"""
    from pathlib import Path
    from datetime import datetime

    marker = Path(__file__).resolve().parent / "data" / ".last_update"
    today = datetime.now().strftime("%Y-%m-%d")

    if marker.exists():
        try:
            with open(marker, "r") as f:
                last = f.read().strip()
            if last == today:
                logger.info(f"数据已是最新 ({today})")
                return
        except (FileNotFoundError, IOError) as e:
            logger.warning(f"读取数据更新标记失败: {e}")

    logger.info("数据未更新，后台启动每日更新...")
    import threading
    def _bg_update():
        try:
            from scripts.daily_update import run
            run(skip_retrain=True)
        except Exception as e:
            logger.error(f"后台更新失败: {e}")

    threading.Thread(target=_bg_update, daemon=True).start()

# 创建FastAPI应用
app = FastAPI(
    title="NBA预测系统 - 算法层",
    description="NBA球员与球队表现预测算法服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(player.router, prefix="/algorithm/player", tags=["球员算法"])
app.include_router(team.router, prefix="/algorithm/team", tags=["球队算法"])
app.include_router(odds.router, prefix="/algorithm/odds", tags=["赔率算法"])
app.include_router(series.router, prefix="/algorithm/series", tags=["系列赛算法"])
app.include_router(config.router, prefix="/algorithm/config", tags=["配置管理"])
app.include_router(data.router, prefix="/data", tags=["数据查询"])

@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "nba-predict-algorithm"}

if __name__ == "__main__":
    is_dev = os.getenv("ENV", "dev") == "dev"
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=is_dev,
        log_level="info",
    )
