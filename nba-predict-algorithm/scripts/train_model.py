"""
Ridge 回归模型训练 v2
使用 nba_api 真实高阶数据，特征从 20 扩展到 28
"""
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.db.database import SessionLocal
from app.db.models import GameRecord, TeamData, AlgorithmParamSnapshot

# 训练/验证赛季划分 (10 赛季数据: 前 8 个训练, 后 2 个验证)
TRAIN_SEASONS = [
    "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24",
]
VAL_SEASONS = ["2024-25", "2025-26"]


def load_all_games() -> list:
    """加载所有比赛记录"""
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED",
        ).order_by(GameRecord.game_date).all()
        return [{
            "game_id": g.game_id,
            "season": g.season,
            "game_date": g.game_date,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_playoff": g.is_playoff,
        } for g in games]


def load_team_stats_from_db() -> dict:
    """
    从 TeamData 表加载真实高阶数据
    返回: {(team_id, season): {ppg, oppg, pace, off_rtg, def_rtg, net_rating, ...}}
    """
    with SessionLocal() as db:
        rows = db.query(TeamData).all()

    result = {}
    for td in rows:
        key = (td.team_id, td.season)
        ppg = td.points_per_game or 0
        oppg = td.opponent_points or 0

        # 真实高阶数据（来自 nba_api）
        pace = td.pace or 100.0
        off_rtg = td.offensive_rating or 110.0
        def_rtg = td.defensive_rating or 110.0
        net_rtg = td.net_rating or (off_rtg - def_rtg)

        # 主客场数据
        home_ppg = td.home_ppg or ppg
        away_ppg = td.away_ppg or ppg

        # 新增高阶指标
        ast_pct = td.assist_pct or 0
        reb_pct = td.rebound_pct or 0
        efg_pct = td.effective_fg_pct or 0
        ts_pct = td.true_shooting_pct or 0

        result[key] = {
            "ppg": round(ppg, 1),
            "oppg": round(oppg, 1),
            "win_pct": td.win_percentage or 0.5,
            "home_ppg": round(home_ppg, 1),
            "away_ppg": round(away_ppg, 1),
            "home_away_diff": round(home_ppg - away_ppg, 1),
            "pace": round(pace, 1),
            "off_rtg": round(off_rtg, 1),
            "def_rtg": round(def_rtg, 1),
            "net_rating": round(net_rtg, 1),
            "recent_wr": td.recent_win_rate or (td.win_percentage or 0.5),
            "momentum": td.momentum or ppg,
            "ast_pct": round(ast_pct, 1),
            "reb_pct": round(reb_pct, 1),
            "efg_pct": round(efg_pct, 3),
            "ts_pct": round(ts_pct, 3),
        }

    return result


def compute_recent_stats(games: list) -> dict:
    """从比赛记录计算近 10 场统计 (momentum, recent_wr)"""
    # 按球队按赛季分组
    team_games = defaultdict(list)
    for g in games:
        if g["is_playoff"]:
            continue
        hs = (g["home_team_id"], g["season"])
        as_ = (g["away_team_id"], g["season"])
        team_games[hs].append((g["game_date"], g["home_score"], g["away_score"]))
        team_games[as_].append((g["game_date"], g["away_score"], g["home_score"]))

    result = {}
    for key, glist in team_games.items():
        glist.sort(key=lambda x: x[0])
        recent = glist[-10:]
        recent_wr = sum(1 for _, pf, pa in recent if pf > pa) / max(len(recent), 1)
        momentum = sum(pf for _, pf, _ in recent) / max(len(recent), 1)
        result[key] = {
            "recent_wr": round(recent_wr, 3),
            "momentum": round(momentum, 1),
        }

    return result


def build_features(games: list, team_stats: dict, recent_stats: dict, target_seasons: list) -> tuple:
    """
    为每场比赛构建特征向量 (28 个特征)
    返回: (X, y_home, y_away, season_list, playoff_list)
    """
    X, y_home, y_away, seasons_out, playoffs_out = [], [], [], [], []

    for g in games:
        if g["season"] not in target_seasons:
            continue

        hs = (g["home_team_id"], g["season"])
        as_ = (g["away_team_id"], g["season"])

        h_stats = team_stats.get(hs)
        a_stats = team_stats.get(as_)
        if not h_stats or not a_stats:
            continue

        # 用比赛记录计算的近 10 场数据覆盖（更准确）
        h_recent = recent_stats.get(hs, {})
        a_recent = recent_stats.get(as_, {})
        h_recent_wr = h_recent.get("recent_wr", h_stats["recent_wr"])
        a_recent_wr = a_recent.get("recent_wr", a_stats["recent_wr"])
        h_momentum = h_recent.get("momentum", h_stats["momentum"])
        a_momentum = a_recent.get("momentum", a_stats["momentum"])

        # 28 个特征
        features = [
            # 基础 (8)
            h_stats["ppg"],                                     # 0: home_ppg
            a_stats["ppg"],                                     # 1: away_ppg
            h_stats["oppg"],                                    # 2: home_oppg
            a_stats["oppg"],                                    # 3: away_oppg
            h_stats["win_pct"],                                 # 4: home_win_pct
            a_stats["win_pct"],                                 # 5: away_win_pct
            h_recent_wr,                                        # 6: home_recent_wr
            a_recent_wr,                                        # 7: away_recent_wr

            # 效率 (10)
            h_stats["off_rtg"],                                 # 8: home_off_rtg
            a_stats["off_rtg"],                                 # 9: away_off_rtg
            h_stats["def_rtg"],                                 # 10: home_def_rtg
            a_stats["def_rtg"],                                 # 11: away_def_rtg
            h_stats["net_rating"],                              # 12: home_net_rating
            a_stats["net_rating"],                              # 13: away_net_rating
            h_stats["off_rtg"] - a_stats["def_rtg"],            # 14: home_off_vs_away_def
            a_stats["off_rtg"] - h_stats["def_rtg"],            # 15: away_off_vs_home_def
            h_stats["efg_pct"],                                 # 16: home_efg_pct
            a_stats["efg_pct"],                                 # 17: away_efg_pct

            # 节奏与风格 (6)
            h_stats["pace"],                                    # 18: home_pace
            a_stats["pace"],                                    # 19: away_pace
            h_stats["pace"] - a_stats["pace"],                  # 20: pace_diff
            h_stats["ts_pct"],                                  # 21: home_ts_pct
            a_stats["ts_pct"],                                  # 22: away_ts_pct
            h_stats["efg_pct"] - a_stats["efg_pct"],            # 23: efg_diff

            # 团队协作 (2)
            h_stats["ast_pct"],                                 # 24: home_ast_pct
            a_stats["ast_pct"],                                 # 25: away_ast_pct

            # 场景 (2)
            g["is_playoff"],                                    # 26: is_playoff
            h_stats["home_away_diff"],                          # 27: home_away_diff

            # momentum (用比赛记录计算的)
            h_momentum,                                         # 28: home_momentum
            a_momentum,                                         # 29: away_momentum
        ]

        X.append(features)
        y_home.append(g["home_score"])
        y_away.append(g["away_score"])
        seasons_out.append(g["season"])
        playoffs_out.append(g["is_playoff"])

    return np.array(X), np.array(y_home), np.array(y_away), seasons_out, playoffs_out


# 特征名 (28 + 2 momentum = 30)
FEATURE_NAMES = [
    "home_ppg", "away_ppg", "home_oppg", "away_oppg",
    "home_win_pct", "away_win_pct", "home_recent_wr", "away_recent_wr",
    "home_off_rtg", "away_off_rtg", "home_def_rtg", "away_def_rtg",
    "home_net_rating", "away_net_rating",
    "home_off_vs_away_def", "away_off_vs_home_def",
    "home_efg_pct", "away_efg_pct",
    "home_pace", "away_pace", "pace_diff",
    "home_ts_pct", "away_ts_pct", "efg_diff",
    "home_ast_pct", "away_ast_pct",
    "is_playoff", "home_away_diff",
    "home_momentum", "away_momentum",
]


def train_and_evaluate():
    """训练 Ridge 回归模型 v2 并评估"""
    logger.info("加载比赛数据...")
    all_games = load_all_games()
    logger.info(f"共 {len(all_games)} 场比赛")

    # 从数据库加载真实高阶数据
    logger.info("加载球队高阶数据...")
    team_stats = load_team_stats_from_db()
    logger.info(f"加载 {len(team_stats)} 个球队赛季数据")

    # 从比赛记录计算近 10 场统计
    logger.info("计算近 10 场统计...")
    recent_stats = compute_recent_stats(all_games)
    logger.info(f"计算 {len(recent_stats)} 个球队赛季近 10 场数据")

    # 构建训练集
    logger.info("构建训练集...")
    X_train, y_home_train, y_away_train, _, _ = build_features(
        all_games, team_stats, recent_stats, TRAIN_SEASONS
    )
    logger.info(f"训练集: {len(X_train)} 场")

    # 构建验证集
    logger.info("构建验证集...")
    X_val, y_home_val, y_away_val, val_seasons, _ = build_features(
        all_games, team_stats, recent_stats, VAL_SEASONS
    )
    logger.info(f"验证集: {len(X_val)} 场")

    if len(X_train) < 100:
        logger.error("训练数据不足")
        return

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Alpha 网格搜索
    logger.info("Alpha 超参数搜索...")
    best_alpha = 1.0
    best_mae = float("inf")

    for alpha in [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
        model_h = Ridge(alpha=alpha)
        model_a = Ridge(alpha=alpha)
        model_h.fit(X_train_scaled, y_home_train)
        model_a.fit(X_train_scaled, y_away_train)

        pred_h = np.round(model_h.predict(X_val_scaled))
        pred_a = np.round(model_a.predict(X_val_scaled))
        mae_total = np.mean(np.abs(pred_h + pred_a - y_home_val - y_away_val))
        mae_diff = np.mean(np.abs((pred_h - pred_a) - (y_home_val - y_away_val)))
        combined = mae_total + mae_diff

        if combined < best_mae:
            best_mae = combined
            best_alpha = alpha

        logger.info(f"  alpha={alpha:.2f}: MAE(总分)={mae_total:.2f}, MAE(分差)={mae_diff:.2f}")

    logger.info(f"最优 alpha: {best_alpha}")

    # 用最优 alpha 训练最终模型
    model_home = Ridge(alpha=best_alpha)
    model_away = Ridge(alpha=best_alpha)
    model_home.fit(X_train_scaled, y_home_train)
    model_away.fit(X_train_scaled, y_away_train)

    # 训练集评估
    pred_home_train = model_home.predict(X_train_scaled)
    pred_away_train = model_away.predict(X_train_scaled)
    train_mae_home = np.mean(np.abs(pred_home_train - y_home_train))
    train_mae_away = np.mean(np.abs(pred_away_train - y_away_train))
    logger.info(f"训练集 MAE: 主队={train_mae_home:.2f}, 客队={train_mae_away:.2f}")

    # 验证集评估
    pred_home_val = model_home.predict(X_val_scaled)
    pred_away_val = model_away.predict(X_val_scaled)
    pred_home_int = np.round(pred_home_val).astype(int)
    pred_away_int = np.round(pred_away_val).astype(int)

    mae_total = np.mean(np.abs(pred_home_int + pred_away_int - y_home_val - y_away_val))
    mae_diff = np.mean(np.abs((pred_home_int - pred_away_int) - (y_home_val - y_away_val)))
    correct = np.sum((pred_home_int > pred_away_int) == (y_home_val > y_away_val))
    win_acc = correct / len(y_home_val)

    logger.info("=" * 50)
    logger.info("验证集结果 (Ridge 回归 v2):")
    logger.info(f"  MAE(总分): {mae_total:.2f}")
    logger.info(f"  MAE(分差): {mae_diff:.2f}")
    logger.info(f"  胜率准确度: {win_acc:.1%}")
    logger.info(f"  验证场次: {len(y_home_val)}")

    # 分赛季验证
    val_seasons_arr = np.array(val_seasons)
    for vs in VAL_SEASONS:
        mask = np.where(val_seasons_arr == vs)[0]
        if len(mask) == 0:
            continue

        ph = pred_home_int[mask]
        pa = pred_away_int[mask]
        ah = y_home_val[mask]
        aa = y_away_val[mask]

        s_mae_total = np.mean(np.abs(ph + pa - ah - aa))
        s_mae_diff = np.mean(np.abs((ph - pa) - (ah - aa)))
        s_correct = np.sum((ph > pa) == (ah > aa))
        s_win_acc = s_correct / len(ah)

        logger.info(f"\n  {vs}:")
        logger.info(f"    MAE(总分)={s_mae_total:.2f}, MAE(分差)={s_mae_diff:.2f}, 胜率={s_win_acc:.1%}")

    # 与旧模型对比
    logger.info("\n" + "=" * 50)
    logger.info("与旧模型对比:")
    logger.info(f"  ridge_v1: MAE(总分)≈16.61, MAE(分差)≈10.82, 胜率≈68.7%")
    logger.info(f"  ridge_v2: MAE(总分)={mae_total:.2f}, MAE(分差)={mae_diff:.2f}, 胜率={win_acc:.1%}")

    # 保存模型参数
    model_params = {
        "model_type": "ridge_regression",
        "version": "ridge_v2",
        "features": FEATURE_NAMES,
        "alpha": best_alpha,
        "home_coefficients": {name: round(float(c), 4) for name, c in zip(FEATURE_NAMES, model_home.coef_)},
        "away_coefficients": {name: round(float(c), 4) for name, c in zip(FEATURE_NAMES, model_away.coef_)},
        "home_intercept": round(float(model_home.intercept_), 2),
        "away_intercept": round(float(model_away.intercept_), 2),
        "scaler_mean": {name: round(float(m), 2) for name, m in zip(FEATURE_NAMES, scaler.mean_)},
        "scaler_scale": {name: round(float(s), 2) for name, s in zip(FEATURE_NAMES, scaler.scale_)},
        "validation_mae_total": round(float(mae_total), 2),
        "validation_mae_diff": round(float(mae_diff), 2),
        "validation_win_acc": round(float(win_acc), 4),
    }

    # 保存到 AlgorithmParamSnapshot
    with SessionLocal() as db:
        existing = db.query(AlgorithmParamSnapshot).filter(
            AlgorithmParamSnapshot.is_current == 1
        ).all()
        for e in existing:
            e.is_current = 0

        snapshot = AlgorithmParamSnapshot(
            version="ridge_v2",
            param_json=json.dumps(model_params, ensure_ascii=False),
            mae_score=round(float(mae_total + mae_diff), 3),
            is_current=1,
        )
        db.add(snapshot)
        db.commit()

    # 保存到文件
    report_path = Path(__file__).resolve().parent.parent / "data" / "ridge_model.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(model_params, f, ensure_ascii=False, indent=2)

    logger.info(f"\n模型参数已保存:")
    logger.info(f"  DB: AlgorithmParamSnapshot (version=ridge_v2)")
    logger.info(f"  文件: {report_path}")

    # 打印特征重要性
    logger.info("\n特征重要性 (home 模型系数 top 10):")
    coef_abs = [(name, abs(float(c))) for name, c in zip(FEATURE_NAMES, model_home.coef_)]
    coef_abs.sort(key=lambda x: x[1], reverse=True)
    for name, imp in coef_abs[:10]:
        logger.info(f"  {name}: {imp:.4f}")

    return model_params


if __name__ == "__main__":
    train_and_evaluate()
