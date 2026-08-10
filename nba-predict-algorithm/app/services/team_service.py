"""
球队服务 - 真实预测逻辑
"""
import json
from pathlib import Path
from loguru import logger
from typing import Optional

from app.models.schemas import TeamPredictRequest, TeamPredictResponse
from app.db.team_dao import TeamDAO
from app.db.player_dao import PlayerDAO
from app.db.config_dao import ConfigDAO
from app.db.models import Player
from app.db.database import SessionLocal
from config.settings import CLUSTERING_CONFIG, ARROW_PLAYER_CONFIG, DATA_DIR

# Ridge 模型缓存
_ridge_model = None


def _load_ridge_model():
    """加载 Ridge 回归模型参数"""
    global _ridge_model
    if _ridge_model is not None:
        return _ridge_model
    model_path = DATA_DIR / "ridge_model.json"
    if model_path.exists():
        with open(model_path, "r", encoding="utf-8") as f:
            _ridge_model = json.load(f)
        logger.info("已加载 Ridge 回归模型")
    return _ridge_model


class TeamService:

    def __init__(self):
        self.team_dao = TeamDAO()
        self.player_dao = PlayerDAO()
        self.config_dao = ConfigDAO()

    def predict(self, request: TeamPredictRequest) -> TeamPredictResponse:
        """预测球队对战结果"""
        home_team = self.team_dao.get_team(request.home_team_id)
        away_team = self.team_dao.get_team(request.away_team_id)
        if not home_team or not away_team:
            return self._fallback_response(request, "球队不存在")

        season = "2025-26"
        home_data = self.team_dao.get_team_data(request.home_team_id, season)
        away_data = self.team_dao.get_team_data(request.away_team_id, season)
        if not home_data or not away_data:
            return self._fallback_response(request, "无赛季数据")

        # 核心预测（Ridge回归 或 手调系数）
        predict_home, predict_away, predict_total, predict_diff, coefficients, style_matchup = \
            self._core_predict(home_data, away_data, request)
        logger.info(f"[预测诊断] {home_team.team_name}(主) vs {away_team.team_name}(客): "
                    f"主={predict_home} 客={predict_away} 分差={predict_diff} "
                    f"主队 net={getattr(home_data, 'net_rating', '?')} "
                    f"off={getattr(home_data, 'offensive_rating', '?')} "
                    f"def={getattr(home_data, 'defensive_rating', '?')} "
                    f"客队 net={getattr(away_data, 'net_rating', '?')} "
                    f"off={getattr(away_data, 'offensive_rating', '?')} "
                    f"def={getattr(away_data, 'defensive_rating', '?')}")

        # 伤病影响调整
        predict_home, predict_away, predict_total, predict_diff, coefficients = \
            self._apply_injury_adjustments(
                predict_home, predict_away, predict_total, predict_diff,
                coefficients, request.home_team_id, request.away_team_id
            )

        # 赔率融合
        resp_home_odds, resp_away_odds, resp_total_odds, resp_diff_odds = \
            self._apply_odds_fusion(request, home_data, away_data,
                                     predict_home, predict_away, predict_total, predict_diff)

        coefficients["odds_weight"] = 0.20 if request.use_odds else 0

        # 计算胜率
        home_win_prob = self._calc_win_probability(home_data, away_data)

        return TeamPredictResponse(
            home_team_id=request.home_team_id,
            home_team_name=home_team.team_name,
            away_team_id=request.away_team_id,
            away_team_name=away_team.team_name,
            scene=request.scene,
            home_win_prob=round(home_win_prob, 3),
            predict_home_score=predict_home,
            predict_away_score=predict_away,
            predict_total_score=predict_total,
            predict_score_diff=predict_diff,
            predict_home_score_odds=resp_home_odds,
            predict_away_score_odds=resp_away_odds,
            predict_total_score_odds=resp_total_odds,
            predict_score_diff_odds=resp_diff_odds,
            coefficients=coefficients,
            style_matchup=style_matchup,
        )

    def _core_predict(self, home_data, away_data, request) -> tuple:
        """核心预测逻辑：优先 Ridge 回归，降级到手调系数"""
        ridge = _load_ridge_model()
        if ridge:
            predict_home, predict_away = self._predict_ridge(
                home_data, away_data, request.scene, ridge
            )
            coefficients = {"model": "ridge_v1"}
            style_matchup = self._calc_style_matchup_simple(home_data, away_data)
        else:
            home_strength_c = self._calc_strength_coeff(home_data)
            away_strength_c = self._calc_strength_coeff(away_data)
            home_c = self._calc_home_coeff(home_data)
            home_fatigue_c = self._calc_fatigue_coeff(request.home_team_id)
            away_fatigue_c = self._calc_fatigue_coeff(request.away_team_id)
            scene_c = self._calc_scene_coeff(request.scene)
            style_matchup, style_c = self._calc_style_matchup(home_data, away_data)

            home_total = home_strength_c * home_c * home_fatigue_c * scene_c * style_c
            away_total = away_strength_c * away_fatigue_c * scene_c

            base_home = home_data.points_per_game or 110.0
            base_away = away_data.points_per_game or 108.0

            predict_home = round(base_home * home_total)
            predict_away = round(base_away * away_total)
            coefficients = {
                "model": "legacy",
                "home_strength": round(home_strength_c, 3),
                "away_strength": round(away_strength_c, 3),
                "home_advantage": round(home_c, 3),
                "home_fatigue": round(home_fatigue_c, 3),
                "away_fatigue": round(away_fatigue_c, 3),
                "scene_coeff": round(scene_c, 3),
                "style_coeff": round(style_c, 3),
            }

        predict_total = predict_home + predict_away
        predict_diff = predict_home - predict_away
        return predict_home, predict_away, predict_total, predict_diff, coefficients, style_matchup

    def _apply_injury_adjustments(self, predict_home, predict_away, predict_total,
                                   predict_diff, coefficients, home_id, away_id) -> tuple:
        """应用伤病影响调整"""
        home_injury = self._calc_injury_impact(home_id)
        away_injury = self._calc_injury_impact(away_id)

        has_injury = (
            home_injury["off_penalty"] > 0 or away_injury["off_penalty"] > 0
            or home_injury.get("chemistry_penalty", 0) > 0
            or away_injury.get("chemistry_penalty", 0) > 0
        )

        if not has_injury:
            return predict_home, predict_away, predict_total, predict_diff, coefficients

        h_chem = home_injury.get("chemistry_penalty", 0)
        a_chem = away_injury.get("chemistry_penalty", 0)

        injury_home = (
            predict_home * (1 - home_injury["off_penalty"] - h_chem)
            + predict_home * away_injury["def_penalty"]
        )
        injury_away = (
            predict_away * (1 - away_injury["off_penalty"] - a_chem)
            + predict_away * home_injury["def_penalty"]
        )

        predict_home = round(injury_home)
        predict_away = round(injury_away)
        predict_total = predict_home + predict_away
        predict_diff = predict_home - predict_away

        coefficients["home_injury_off_penalty"] = home_injury["off_penalty"]
        coefficients["home_injury_def_penalty"] = home_injury["def_penalty"]
        coefficients["home_chemistry_penalty"] = h_chem
        coefficients["away_injury_off_penalty"] = away_injury["off_penalty"]
        coefficients["away_injury_def_penalty"] = away_injury["def_penalty"]
        coefficients["away_chemistry_penalty"] = a_chem
        coefficients["injury_details"] = {
            "home": home_injury["details"],
            "away": away_injury["details"],
        }
        return predict_home, predict_away, predict_total, predict_diff, coefficients

    def _apply_odds_fusion(self, request, home_data, away_data,
                            predict_home, predict_away, predict_total, predict_diff) -> tuple:
        """应用赔率融合"""
        resp_home_odds = None
        resp_away_odds = None
        resp_total_odds = None
        resp_diff_odds = None

        if not request.use_odds:
            return resp_home_odds, resp_away_odds, resp_total_odds, resp_diff_odds

        odds = self.team_dao.get_latest_odds(request.home_team_id, request.away_team_id)
        if not odds:
            return resp_home_odds, resp_away_odds, resp_total_odds, resp_diff_odds

        coeffs = self.config_dao.get_coefficients()
        odds_weight = coeffs.get("odds_weight", 0.20)

        if odds.home_win_prob and odds.away_win_prob:
            base_home = home_data.points_per_game or 110.0
            base_away = away_data.points_per_game or 108.0
            odds_home = round(base_home * (1.0 + (odds.home_win_prob - 0.5) * 0.2))
            odds_away = round(base_away * (1.0 + (odds.away_win_prob - 0.5) * 0.2))
            resp_home_odds = round(predict_home * (1 - odds_weight) + odds_home * odds_weight)
            resp_away_odds = round(predict_away * (1 - odds_weight) + odds_away * odds_weight)
            resp_total_odds = resp_home_odds + resp_away_odds
            resp_diff_odds = resp_home_odds - resp_away_odds

        if odds.total_line:
            resp_total_odds = round(predict_total * (1 - odds_weight) + odds.total_line * odds_weight)
            resp_diff_odds = round(predict_diff * (1 - odds_weight) + (odds.handicap_line or predict_diff) * odds_weight)

        return resp_home_odds, resp_away_odds, resp_total_odds, resp_diff_odds

    def _predict_ridge(self, home_data, away_data, scene: str, ridge: dict) -> tuple:
        """用 Ridge 回归模型预测 (v2: 使用真实高阶数据)"""
        is_playoff = 1 if scene == "季后赛" else 0

        # 真实数据（来自 nba_api）
        h_ppg = home_data.points_per_game or 110.0
        h_oppg = home_data.opponent_points or 110.0
        a_ppg = away_data.points_per_game or 108.0
        a_oppg = away_data.opponent_points or 110.0

        h_off_rtg = home_data.offensive_rating or 110.0
        h_def_rtg = home_data.defensive_rating or 110.0
        a_off_rtg = away_data.offensive_rating or 110.0
        a_def_rtg = away_data.defensive_rating or 110.0
        h_net_rating = home_data.net_rating or (h_off_rtg - h_def_rtg)
        a_net_rating = away_data.net_rating or (a_off_rtg - a_def_rtg)

        h_pace = home_data.pace or 100.0
        a_pace = away_data.pace or 100.0

        h_home_ppg = home_data.home_ppg or h_ppg
        h_away_ppg = home_data.away_ppg or h_ppg
        h_home_away_diff = h_home_ppg - h_away_ppg

        h_efg = home_data.effective_fg_pct or 0.5
        a_efg = away_data.effective_fg_pct or 0.5
        h_ts = home_data.true_shooting_pct or 0.55
        a_ts = away_data.true_shooting_pct or 0.55
        h_ast = home_data.assist_pct or 15.0
        a_ast = away_data.assist_pct or 15.0

        features = [
            h_ppg, a_ppg, h_oppg, a_oppg,
            home_data.win_percentage or 0.5,
            away_data.win_percentage or 0.5,
            home_data.recent_win_rate or home_data.win_percentage or 0.5,
            away_data.recent_win_rate or away_data.win_percentage or 0.5,
            round(h_off_rtg, 1), round(a_off_rtg, 1),
            round(h_def_rtg, 1), round(a_def_rtg, 1),
            round(h_net_rating, 1), round(a_net_rating, 1),
            round(h_off_rtg - a_def_rtg, 1),
            round(a_off_rtg - h_def_rtg, 1),
            round(h_efg, 3), round(a_efg, 3),
            round(h_pace, 1), round(a_pace, 1),
            round(h_pace - a_pace, 1),
            round(h_ts, 3), round(a_ts, 3),
            round(h_efg - a_efg, 3),
            round(h_ast, 1), round(a_ast, 1),
            is_playoff,
            round(h_home_away_diff, 1),
            home_data.momentum or h_ppg,
            away_data.momentum or a_ppg,
        ]

        # 标准化: (x - mean) / scale
        means = [ridge["scaler_mean"][k] for k in ridge["features"]]
        scales = [ridge["scaler_scale"][k] for k in ridge["features"]]
        scaled = [(f - m) / max(s, 0.001) for f, m, s in zip(features, means, scales)]

        # 预测: w · x + intercept
        home_coefs = [ridge["home_coefficients"][k] for k in ridge["features"]]
        away_coefs = [ridge["away_coefficients"][k] for k in ridge["features"]]

        predict_home = round(sum(c * x for c, x in zip(home_coefs, scaled)) + ridge["home_intercept"])
        predict_away = round(sum(c * x for c, x in zip(away_coefs, scaled)) + ridge["away_intercept"])

        return predict_home, predict_away

    def _calc_style_matchup_simple(self, home_data, away_data) -> str:
        """简化版风格分析 (使用 NetRtg)"""
        h_net = home_data.net_rating or 0
        a_net = away_data.net_rating or 0
        h_off = home_data.offensive_rating or 110.0
        h_def = home_data.defensive_rating or 110.0
        a_off = away_data.offensive_rating or 110.0
        a_def = away_data.defensive_rating or 110.0

        h_type = "进攻型" if h_off > h_def + 2 else ("防守型" if h_def > h_off + 2 else "均衡型")
        a_type = "进攻型" if a_off > a_def + 2 else ("防守型" if a_def > a_off + 2 else "均衡型")
        return f"{h_type}(NetRtg:{h_net:+.1f}) vs {a_type}(NetRtg:{a_net:+.1f})"

    def _get_team_injured_players(self, team_id: int) -> list:
        """获取球队受伤球员列表 (INJURED 或 RECOVERY 状态)"""
        with SessionLocal() as db:
            return db.query(Player).filter(
                Player.team_id == team_id,
                Player.status == 1,
                Player.injury_status.in_(["INJURED", "RECOVERY"]),
                Player.impact_score.isnot(None),
                Player.impact_score > 0,
            ).all()

    def _calc_injury_impact(self, team_id: int) -> dict:
        """
        计算伤病对球队的影响 (15角色 + 化学反应)

        返回:
            off_penalty: 进攻惩罚 (0-0.3)
            def_penalty: 防守惩罚 (0-0.3)
            chemistry_penalty: 化学反应惩罚 (0-0.15)
            details: 伤病详情列表
        """
        injured = self._get_team_injured_players(team_id)
        if not injured:
            return {"off_penalty": 0.0, "def_penalty": 0.0, "chemistry_penalty": 0.0, "details": []}

        total_off_impact = 0.0
        total_def_impact = 0.0
        total_chemistry = 0.0
        details = []

        # 15角色攻防权重 + 化学反应权重
        ROLE_WEIGHTS = {
            #               off   def   chemistry
            "ball_handler":       (1.4, 0.5, 1.0),   # 持球核心: 进攻无疏导
            "defensive_anchor":   (0.4, 1.5, 1.0),   # 防守核心: 防守体系崩塌
            "scorer":             (1.3, 0.5, 0.7),   # 得分机器: 进攻火力下降
            "two_way":            (1.2, 1.2, 1.0),   # 攻防一体: 两端都受影响
            "stretch_big":        (0.9, 0.5, 0.5),   # 空间型内线: 空间缩小
            "rim_protector":      (0.3, 1.4, 0.6),   # 护框型内线: 内线空虚
            "floor_general":      (1.0, 0.3, 1.3),   # 替补指挥官: 衔接段混乱
            "sixth_man":          (1.1, 0.7, 1.2),   # 第六人: 替补火力断层
            "three_and_d":        (0.8, 1.0, 0.4),   # 3D球员: 空间+防守丢失
            "connector":          (0.9, 0.6, 1.4),   # 组织串联: 配合断裂
            "energy_big":         (0.4, 0.8, 0.3),   # 蓝领内线: 篮板下降
            "microwave_scorer":   (0.8, 0.3, 0.3),   # 微波得分手: 替补得分下降
            "spot_up_shooter":    (0.7, 0.2, 0.2),   # 定点射手: 牵制力下降
            "veteran_stabilizer": (0.5, 0.4, 1.5),   # 老将稳定器: 关键时刻无人压阵
            "role_player":        (0.5, 0.5, 0.2),   # 角色球员: 影响有限
        }

        for p in injured:
            role = p.player_role or "role_player"
            off = p.offensive_impact or 0.0
            deff = p.defensive_impact or 0.0
            dep = p.team_dependency or 0.1
            conn = p.connector_score or 0.0
            vet = p.veteran_score or 0.0

            status_factor = 1.0 if p.injury_status == "INJURED" else 0.5

            rw = ROLE_WEIGHTS.get(role, (0.5, 0.5, 0.2))

            player_off = off * rw[0] * dep * status_factor
            player_def = deff * rw[1] * dep * status_factor

            # 化学反应: 串联值 × 化学权重 + 经验值 × 化学权重
            player_chem = (conn * rw[2] * 0.5 + vet * rw[2] * 0.3) * status_factor

            total_off_impact += player_off
            total_def_impact += player_def
            total_chemistry += player_chem

            details.append({
                "player_name": p.player_name,
                "role": role,
                "injury_status": p.injury_status,
                "impact_score": p.impact_score,
                "off_impact": round(player_off, 3),
                "def_impact": round(player_def, 3),
                "chemistry_impact": round(player_chem, 3),
            })

        off_penalty = min(0.30, total_off_impact)
        def_penalty = min(0.30, total_def_impact)
        chemistry_penalty = min(0.15, total_chemistry)

        return {
            "off_penalty": round(off_penalty, 3),
            "def_penalty": round(def_penalty, 3),
            "chemistry_penalty": round(chemistry_penalty, 3),
            "details": details,
        }

    def classify(self, season: str) -> dict:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        teams = self.team_dao.get_teams_with_data(season)
        if len(teams) < 7:
            return {"season": season, "clusters": 0, "status": "数据不足", "message": f"仅{len(teams)}支球队有数据"}

        defense_features, offense_features, team_ids = [], [], []
        for item in teams:
            d = item["data"]
            t = item["team"]
            defense_features.append([
                d.defensive_rating or 0, d.opponent_fg_percentage or 0,
                d.opponent_three_pct or 0, d.steals_per_game or 0,
                d.blocks_per_game or 0, d.rebound_pct or 0,
            ])
            offense_features.append([
                d.offensive_rating or 0, d.three_percentage or 0,
                d.pace or 0, d.effective_fg_pct or 0,
                d.true_shooting_pct or 0, d.assist_pct or 0,
            ])
            team_ids.append(t.team_id)

        def_cl = CLUSTERING_CONFIG["team_defense_clusters"]
        off_cl = CLUSTERING_CONFIG["team_offense_clusters"]
        rs = CLUSTERING_CONFIG["random_state"]

        X_def = StandardScaler().fit_transform(defense_features)
        def_labels = KMeans(n_clusters=def_cl, random_state=rs, n_init=10).fit_predict(X_def)

        X_off = StandardScaler().fit_transform(offense_features)
        off_labels = KMeans(n_clusters=off_cl, random_state=rs, n_init=10).fit_predict(X_off)

        def_names = ["铁血防守", "均衡防守", "防守薄弱"]
        off_names = ["炮轰型", "均衡进攻", "阵地型", "内线型"]

        for tid, dl, ol in zip(team_ids, def_labels, off_labels):
            self.team_dao.update_team_cluster(tid, "defense", int(dl), def_names[dl])
            self.team_dao.update_team_cluster(tid, "offense", int(ol), off_names[ol])

        return {
            "season": season,
            "defense_clusters": def_cl,
            "offense_clusters": off_cl,
            "updated": len(team_ids),
            "status": "聚类完成",
        }

    def get_matchup(self, team1_id: int, team2_id: int) -> dict:
        season = "2025-26"
        team1 = self.team_dao.get_team(team1_id)
        team2 = self.team_dao.get_team(team2_id)
        if not team1 or not team2:
            return {"team1_id": team1_id, "team2_id": team2_id, "error": "球队不存在"}

        history = self.team_dao.get_battle_record(team1_id, team2_id, season)
        h2h_games = self.team_dao.get_head_to_head_games(team1_id, team2_id, limit=10)

        hist_summary = {"total_games": 0, "team1_wins": 0, "team2_wins": 0}
        if history:
            rec = history[0]
            hist_summary = {
                "total_games": rec.total_games,
                "team1_wins": rec.team1_wins,
                "team2_wins": rec.team2_wins,
                "team1_avg_score": rec.team1_avg_score,
                "team2_avg_score": rec.team2_avg_score,
            }

        team1_data = self.team_dao.get_team_data(team1_id, season)
        team2_data = self.team_dao.get_team_data(team2_id, season)

        style_matchup = "待分析"
        advantage_team = None
        if team1_data and team2_data:
            style_matchup, advantage_team = self._analyze_style_matchup(
                team1, team2, team1_data, team2_data
            )

        return {
            "team1_id": team1_id,
            "team1_name": team1.team_name if team1 else "未知",
            "team2_id": team2_id,
            "team2_name": team2.team_name if team2 else "未知",
            "history": hist_summary,
            "style_matchup": style_matchup,
            "advantage_team": advantage_team,
            "recent_games": [
                {
                    "date": str(g.game_date),
                    "home_score": g.home_score,
                    "away_score": g.away_score,
                    "winner": "home" if g.home_win else "away",
                }
                for g in h2h_games[:5]
            ],
        }

    def _calc_strength_coeff(self, team_data) -> float:
        """实力系数: 基于胜率、进攻效率、防守效率"""
        win_pct = team_data.win_percentage or 0.5
        off_rtg = team_data.offensive_rating or 110.0
        def_rtg = team_data.defensive_rating or 110.0

        win_factor = 0.8 + (win_pct * 0.4)
        off_factor = off_rtg / 112.0
        def_factor = 112.0 / max(def_rtg, 90.0)

        return win_factor * 0.4 + off_factor * 0.3 + def_factor * 0.3

    def _calc_home_coeff(self, team_data) -> float:
        """主场优势系数"""
        base = 1.055
        if team_data.home_wins and team_data.home_losses:
            total = team_data.home_wins + team_data.home_losses
            if total > 0:
                home_win_pct = team_data.home_wins / total
                base = 1.03 + (home_win_pct * 0.05)
        return base

    def _calc_fatigue_coeff(self, team_id: int) -> float:
        """疲劳系数: 背靠背检查"""
        if self.team_dao.get_recent_back_to_back(team_id):
            return 0.92
        games = self.team_dao.get_recent_games(team_id, limit=3)
        if len(games) >= 2:
            from datetime import timedelta
            diff = abs((games[0].game_date - games[1].game_date).days)
            if diff <= 2:
                return 0.98
        return 1.0

    def _calc_scene_coeff(self, scene: str) -> float:
        """比赛场景系数"""
        return 1.08 if scene == "季后赛" else 1.0

    def _calc_win_probability(self, home_data, away_data) -> float:
        """基于攻防效率差 + 胜率差 + 主场优势计算胜率"""
        import math

        def _team_net(data):
            """获取球队净效率，优先用 rating，降级用 PPG 差值"""
            off = getattr(data, 'offensive_rating', 0) or 0
            df = getattr(data, 'defensive_rating', 0) or 0
            if off > 50 and df > 50:
                return off - df
            # 兜底：PPG - opponent_pts 作为近似净效率
            ppg = getattr(data, 'points_per_game', 0) or 0
            opp = getattr(data, 'opponent_points', 0) or 0
            return ppg - opp if ppg > 50 else 0

        h_net = _team_net(home_data)
        a_net = _team_net(away_data)
        h_wp = float(getattr(home_data, 'win_percentage', 0.5) or 0.5)
        a_wp = float(getattr(away_data, 'win_percentage', 0.5) or 0.5)
        wp_factor = (h_wp - a_wp) * 40.0
        rating_diff = (h_net - a_net) + wp_factor + 2.5
        return 1.0 / (1.0 + math.exp(-rating_diff / 12.0))

    def get_team_rating(self, team_id: int) -> dict:
        """获取球队实力评分"""
        season = "2025-26"
        with SessionLocal() as db:
            from app.db.models import Team, TeamData
            team = db.query(Team).filter(Team.team_id == team_id).first()
            td = db.query(TeamData).filter(
                TeamData.team_id == team_id, TeamData.season == season
            ).first()
        if not team:
            return {"error": "球队不存在"}
        return {
            "team_id": team_id,
            "team_name": team.team_name,
            "net_rating": td.net_rating if td else None,
            "offensive_rating": td.offensive_rating if td else None,
            "defensive_rating": td.defensive_rating if td else None,
            "pace": td.pace if td else None,
            "win_percentage": float(td.win_percentage) if td and td.win_percentage else None,
        }

    def _calc_style_matchup(self, home_data, away_data) -> tuple:
        """风格克制分析"""
        home_off = home_data.offensive_rating or 110.0
        home_def = home_data.defensive_rating or 110.0
        away_off = away_data.offensive_rating or 110.0
        away_def = away_data.defensive_rating or 110.0

        home_type = "进攻型" if home_off > home_def else "防守型"
        away_type = "进攻型" if away_off > away_def else "防守型"

        style_coeff = 1.0
        desc = f"{home_type} vs {away_type}"

        if home_type == "进攻型" and away_type == "防守型":
            three_pct = away_data.opponent_three_pct or 0.35
            if three_pct < 0.34:
                desc += " - 防守型克制"
                style_coeff = 0.95
            else:
                desc += " - 进攻型占优"
                style_coeff = 1.03
        elif home_type == "防守型" and away_type == "进攻型":
            three_pct = home_data.three_percentage or 0.35
            if three_pct > 0.38:
                desc += " - 进攻型克制"
                style_coeff = 1.03
            else:
                desc += " - 防守型占优"
                style_coeff = 0.97
        else:
            desc += " - 均衡对决"

        return desc, style_coeff

    def _analyze_style_matchup(self, team1, team2, data1, data2) -> tuple:
        """分析两队风格克制关系"""
        off1 = data1.offensive_rating or 110.0
        def1 = data1.defensive_rating or 110.0
        off2 = data2.offensive_rating or 110.0
        def2 = data2.defensive_rating or 110.0

        type1 = "进攻型" if off1 > def1 + 2 else ("防守型" if def1 > off1 + 2 else "均衡型")
        type2 = "进攻型" if off2 > def2 + 2 else ("防守型" if def2 > off2 + 2 else "均衡型")

        advantage = None
        if type1 != type2 and type1 != "均衡型" and type2 != "均衡型":
            if type1 == "进攻型" and type2 == "防守型":
                opp_fg = data2.opponent_fg_percentage or 0.45
                advantage = team1.team_name if opp_fg > 0.46 else team2.team_name
            else:
                opp_fg = data1.opponent_fg_percentage or 0.45
                advantage = team2.team_name if opp_fg > 0.46 else team1.team_name
        else:
            wp1 = data1.win_percentage or 0.5
            wp2 = data2.win_percentage or 0.5
            advantage = team1.team_name if wp1 > wp2 else team2.team_name

        return f"{type1} vs {type2}", advantage

    def _fallback_response(self, request, reason="数据不足") -> TeamPredictResponse:
        logger.warning(f"球队预测降级: {reason}")
        return TeamPredictResponse(
            home_team_id=request.home_team_id,
            home_team_name="主队",
            away_team_id=request.away_team_id,
            away_team_name="客队",
            scene=request.scene,
            predict_home_score=110,
            predict_away_score=105,
            predict_total_score=215,
            predict_score_diff=5,
            coefficients={"error": reason},
            style_matchup=reason,
        )
