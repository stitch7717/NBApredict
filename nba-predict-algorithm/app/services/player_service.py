"""
球员服务 - 真实预测逻辑
"""
from loguru import logger
from typing import Optional

from app.models.schemas import PlayerPredictRequest, PlayerPredictResponse
from app.db.player_dao import PlayerDAO
from app.db.config_dao import ConfigDAO
from config.settings import COEFFICIENT_CONFIG


class PlayerService:

    def __init__(self):
        self.player_dao = PlayerDAO()
        self.config_dao = ConfigDAO()

    def _get_coeff_config(self) -> dict:
        """获取系数配置（静态值，由回测脚本 tune_coefficients.py 调优后更新）"""
        return COEFFICIENT_CONFIG

    def predict(self, request: PlayerPredictRequest) -> PlayerPredictResponse:
        player = self.player_dao.get_player(request.player_id)
        if not player:
            return self._fallback_response(request, "球员不存在")

        season = "2025-26"
        player_data = self.player_dao.get_player_data(request.player_id, season)
        if not player_data:
            return self._fallback_response(request, player.player_name, "无赛季数据")

        coeffs = self.config_dao.get_coefficients()

        all_star_c = self._calc_all_star_coeff(player)
        veteran_c = self._calc_veteran_coeff(player)
        injury_c = self._calc_injury_coeff(player)
        clutch_c = self._calc_clutch_coeff(request.scene)
        home_c = self._calc_home_coeff(request.home_away)
        fatigue_c = self._calc_fatigue_coeff(request.player_id)
        stability_c = self._calc_stability_coeff(player_data)

        total_c = all_star_c * veteran_c * injury_c * clutch_c * home_c * fatigue_c * stability_c

        base_points = player_data.points_per_game or 10.0
        base_fg_pct = player_data.fg_percentage or 0.45
        points_std = player_data.points_std or (base_points * 0.25)

        mid = base_points * total_c
        low = max(0, mid - 1.5 * points_std)
        high = mid + 1.5 * points_std
        fg_pct = min(0.75, base_fg_pct * (total_c ** 0.3))

        tags = self._generate_matchup_tags(player, player_data)

        return PlayerPredictResponse(
            player_id=request.player_id,
            player_name=player.player_name,
            scene=request.scene,
            points_low=round(low, 1),
            points_mid=round(mid, 1),
            points_high=round(high, 1),
            fg_pct=round(fg_pct, 3),
            all_star_coeff=round(all_star_c, 3),
            veteran_coeff=round(veteran_c, 3),
            injury_coeff=round(injury_c, 3),
            clutch_coeff=round(clutch_c, 3),
            home_coeff=round(home_c, 3),
            fatigue_coeff=round(fatigue_c, 3),
            total_coeff=round(total_c, 3),
            matchup_tags=tags,
        )

    def classify(self, season: str) -> dict:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        players = self.player_dao.get_players_with_data(season)
        if len(players) < 7:
            return {"season": season, "clusters": 0, "status": "数据不足", "message": f"仅{len(players)}名球员有数据"}

        features, player_ids = [], []
        for item in players:
            d = item["data"]
            features.append([
                d.per or 0, d.true_shooting_pct or 0,
                d.usage_rate or 0, d.assist_pct or 0,
                d.rebound_pct or 0, d.steal_pct or 0,
                d.block_pct or 0, d.net_rating or 0,
            ])
            player_ids.append(item["player"].player_id)

        X = StandardScaler().fit_transform(features)
        labels = KMeans(n_clusters=7, random_state=42, n_init=10).fit_predict(X)

        names = ["得分型", "组织型", "3D型", "内线型", "全能型", "防守型", "替补型"]
        for pid, label in zip(player_ids, labels):
            self.player_dao.update_player_cluster(pid, int(label), names[label])

        return {"season": season, "clusters": 7, "updated": len(player_ids), "status": "聚类完成"}

    def get_coefficients(self, player_id: int, scene: str) -> dict:
        player = self.player_dao.get_player(player_id)
        if not player:
            return {"player_id": player_id, "error": "球员不存在"}

        return {
            "player_id": player_id,
            "scene": scene,
            "player_name": player.player_name,
            "coefficients": {
                "all_star_coeff": round(self._calc_all_star_coeff(player), 3),
                "veteran_coeff": round(self._calc_veteran_coeff(player), 3),
                "injury_coeff": round(self._calc_injury_coeff(player), 3),
            }
        }

    def _calc_all_star_coeff(self, player) -> float:
        cfg = self._get_coeff_config()
        count = player.all_star_count or 0
        base = cfg.get("all_star_coeff", {}).get("value", 1.20)
        coeff_range = cfg.get("all_star_coeff", {})
        min_v, max_v = coeff_range.get("min", 1.0), coeff_range.get("max", 1.40)
        if count == 0: return 1.0
        elif count <= 2: return round(base - 0.10, 2)
        elif count <= 5: return base
        elif count <= 8: return round(base + 0.10, 2)
        else: return max_v

    def _calc_veteran_coeff(self, player) -> float:
        cfg = self._get_coeff_config()
        base = cfg.get("veteran_coeff", {}).get("value", 0.875)
        age = player.age or 25
        if age < 30: return 1.0
        elif age < 33: return round(base + 0.075, 2)
        elif age < 36: return base
        else: return round(base - 0.075, 2)

    def _calc_injury_coeff(self, player) -> float:
        cfg = self._get_coeff_config()
        base = cfg.get("injury_coeff", {}).get("value", 0.85)
        status = player.injury_status or "HEALTHY"
        if status == "HEALTHY": return 1.0
        elif status == "RECOVERY": return base
        elif status == "INJURED": return round(base - 0.15, 2)
        return 1.0

    def _calc_clutch_coeff(self, scene: str) -> float:
        return 1.10 if scene == "季后赛" else 1.0

    def _calc_home_coeff(self, home_away: str) -> float:
        return 1.055 if home_away == "home" else 0.97

    def _calc_fatigue_coeff(self, player_id: int) -> float:
        player = self.player_dao.get_player(player_id)
        if not player or not player.team_id:
            return 1.0
        games = self.player_dao.get_player_recent_games(player_id, limit=3)
        if len(games) >= 2:
            from datetime import timedelta
            diff = abs((games[0].game_date - games[1].game_date).days)
            if diff <= 1: return 0.92
            elif diff <= 2: return 0.98
        return 1.0

    def _calc_stability_coeff(self, player_data) -> float:
        cv = player_data.points_cv
        if cv is None: return 1.0
        if cv < 0.20: return 1.0
        elif cv < 0.30: return 0.97
        elif cv < 0.40: return 0.93
        else: return 0.85

    def _generate_matchup_tags(self, player, player_data) -> list:
        tags = []
        if player.player_type: tags.append(player.player_type)
        if player_data.isolation_pct and player_data.isolation_pct > 15: tags.append("单打型")
        if player_data.pick_roll_pct and player_data.pick_roll_pct > 20: tags.append("挡拆型")
        if player_data.spot_up_pct and player_data.spot_up_pct > 20: tags.append("投射型")
        if player_data.three_percentage and player_data.three_percentage > 0.38: tags.append("外线为主")
        if player_data.usage_rate and player_data.usage_rate > 28: tags.append("高使用率")
        if player_data.net_rating and player_data.net_rating > 5: tags.append("高影响力")
        if player_data.assist_pct and player_data.assist_pct > 25: tags.append("组织核心")
        if player_data.rebound_pct and player_data.rebound_pct > 15: tags.append("篮板手")
        if player.all_star_count and player.all_star_count > 0: tags.append(f"全明星x{player.all_star_count}")
        return tags if tags else ["普通球员"]

    def _fallback_response(self, request, name="未知", reason="数据不足") -> PlayerPredictResponse:
        logger.warning(f"球员预测降级: {name}, 原因: {reason}")
        return PlayerPredictResponse(
            player_id=request.player_id, player_name=name, scene=request.scene,
            points_low=8.0, points_mid=15.0, points_high=22.0, fg_pct=0.450,
            all_star_coeff=1.0, veteran_coeff=1.0, injury_coeff=1.0,
            clutch_coeff=1.0, home_coeff=1.0, fatigue_coeff=1.0,
            total_coeff=1.0, matchup_tags=[reason],
        )
