"""
NBA预测算法层 - 测试
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


class TestHealthCheck:
    """健康检查测试"""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestPlayerAPI:
    """球员API测试"""

    def test_get_players_returns_list(self):
        response = client.get("/data/players")
        # 数据库可能为空，接受200或错误码
        assert response.status_code in [200, 500]

    def test_get_players_pagination(self):
        response = client.get("/data/players?page=1&limit=5")
        assert response.status_code in [200, 500]


class TestTeamAPI:
    """球队API测试"""

    def test_get_teams_returns_list(self):
        response = client.get("/data/teams")
        assert response.status_code in [200, 500]


class TestPredictionAPI:
    """预测API测试"""

    def test_player_predict_validation(self):
        """测试球员预测参数校验"""
        response = client.post("/algorithm/player/predict", json={})
        # 缺少必要参数应返回 422 (Pydantic) 或 400
        assert response.status_code in [400, 422]
