"""
补充经典模型对比（走查式回测，与主对比实验同一套划分与特征）

补齐论文中常见的经典模型，使对比覆盖面完整：
  回归路径：Lasso / ElasticNet / KNN / 线性SVR / 多层感知机 / 单棵决策树 / ExtraTrees
  分类路径：高斯朴素贝叶斯
  集  成  ：Ridge + XGBoost 简单平均

公平性：与 backtest_model_comparison.py 完全相同的
  特征矩阵（mode_b_features，19 维）、走查折（TEST_SEASONS）、
  标准化方式（每折只在训练集上 fit）。

用法:
    python scripts/backtest_more_models.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVR
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

from scripts.backtest_model_comparison import (
    SIGMOID_SCALE,
    metrics,
    sigmoid_from_diff,
)
from scripts.backtest_seasons import TEST_SEASONS, load_all_games, mode_b_features

# 主对比实验已有结果（供对照，避免重复跑慢模型）
REFERENCE = [
    ("线性回归 OLS", 0.6512, 15.05, 0.2190),
    ("Ridge (alpha=1.0)", 0.6520, 15.05, 0.2189),
    ("逻辑回归（分类路径）", 0.6520, None, 0.2187),
    ("XGBoost（调参后最优 depth=3）", 0.6351, 15.22, 0.2233),
    ("随机森林", 0.6255, 15.42, 0.2271),
]


def walk_predict(factory, X, y_home, y_away, seasons):
    """走查式回测，返回预测值（供计算指标与集成）"""
    seasons_arr = np.array(seasons)
    yh_all, ya_all, ph_all, pa_all = [], [], [], []
    secs = 0.0
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])
        t0 = time.perf_counter()
        m_h = factory().fit(X_tr, y_home[train_mask])
        m_a = factory().fit(X_tr, y_away[train_mask])
        secs += time.perf_counter() - t0
        ph_all.append(m_h.predict(X_te))
        pa_all.append(m_a.predict(X_te))
        yh_all.append(y_home[test_mask])
        ya_all.append(y_away[test_mask])
    return (np.concatenate(ph_all), np.concatenate(pa_all),
            np.concatenate(yh_all), np.concatenate(ya_all), secs)


def walk_predict_proba(factory, X, y_home, y_away, seasons):
    """分类路径：返回 P(主胜)"""
    seasons_arr = np.array(seasons)
    y_win = (y_home > y_away).astype(int)
    p_all, yh_all, ya_all = [], [], []
    secs = 0.0
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])
        t0 = time.perf_counter()
        m = factory().fit(X_tr, y_win[train_mask])
        secs += time.perf_counter() - t0
        p_all.append(m.predict_proba(X_te)[:, 1])
        yh_all.append(y_home[test_mask])
        ya_all.append(y_away[test_mask])
    return (np.concatenate(p_all), np.concatenate(yh_all),
            np.concatenate(ya_all), secs)


def report(name, ph, pa, yh, ya, secs):
    y_win = (yh > ya).astype(float)
    m = metrics(yh, ya, ph, pa, y_win, sigmoid_from_diff(ph - pa))
    logger.info(f"{name:<34}{m['win_acc']:>9.2%}{m['mae_total']:>10.2f}"
                f"{m['mae_diff']:>10.2f}{m['brier']:>9.4f}{secs:>9.1f}")
    return m


def main():
    games = load_all_games()
    X, y_home, y_away, seasons, playoffs, _ = mode_b_features(games)
    X = np.asarray(X, dtype=float)
    logger.info(f"样本 {len(X)} 场, 特征 {X.shape[1]} 维, 走查 9 折\n")

    header = f"{'模型':<34}{'胜率':>9}{'MAE总分':>10}{'MAE分差':>10}{'Brier':>9}{'训练(s)':>9}"

    logger.info("=" * 82)
    logger.info("参照：主对比实验已跑过的模型")
    logger.info("=" * 82)
    logger.info(header)
    logger.info("-" * 82)
    for name, acc, mae, brier in REFERENCE:
        mae_s = f"{mae:>10.2f}" if mae is not None else f"{'—':>10}"
        logger.info(f"{name:<34}{acc:>9.2%}{mae_s}{'—':>10}{brier:>9.4f}{'—':>9}")
    logger.info("")

    logger.info("=" * 82)
    logger.info("本轮新增：回归路径")
    logger.info("=" * 82)
    logger.info(header)
    logger.info("-" * 82)

    regression = {
        "Lasso (L1, alpha=0.01)": lambda: Lasso(alpha=0.01, max_iter=5000),
        "ElasticNet (L1+L2, alpha=0.01)": lambda: ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=5000),
        "KNN 回归 (k=25)": lambda: KNeighborsRegressor(n_neighbors=25, n_jobs=-1),
        "线性支持向量回归 LinearSVR": lambda: LinearSVR(C=1.0, max_iter=5000, random_state=42),
        "多层感知机 MLP (64,32)": lambda: MLPRegressor(
            hidden_layer_sizes=(64, 32), max_iter=500, early_stopping=True, random_state=42
        ),
        "单棵决策树 (depth=8)": lambda: DecisionTreeRegressor(max_depth=8, random_state=42),
        "ExtraTrees (n=300)": lambda: ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=42
        ),
    }

    results = {}
    preds = {}
    for name, factory in regression.items():
        ph, pa, yh, ya, secs = walk_predict(factory, X, y_home, y_away, seasons)
        results[name] = report(name, ph, pa, yh, ya, secs)
        preds[name] = (ph, pa, yh, ya)
    logger.info("")

    logger.info("=" * 82)
    logger.info("本轮新增：分类路径 + 集成")
    logger.info("=" * 82)
    logger.info(header)
    logger.info("-" * 82)

    # 高斯朴素贝叶斯
    p, yh, ya, secs = walk_predict_proba(
        lambda: GaussianNB(), X, y_home, y_away, seasons
    )
    y_win = (yh > ya).astype(float)
    nb = {"n": len(yh), "win_acc": float(np.mean((p > 0.5) == (y_win > 0.5))),
          "mae_total": float("nan"), "mae_diff": float("nan"),
          "brier": float(np.mean((p - y_win) ** 2))}
    logger.info(f"{'高斯朴素贝叶斯':<34}{nb['win_acc']:>9.2%}{'—':>10}{'—':>10}"
                f"{nb['brier']:>9.4f}{secs:>9.1f}")

    # 集成：Ridge + XGBoost 平均
    # 说明：为避免重跑，用 Ridge 与 XGBoost 的预测做等权平均
    ridge = walk_predict(lambda: Ridge(alpha=1.0), X, y_home, y_away, seasons)
    xgb = walk_predict(
        lambda: XGBRegressor(
            max_depth=3, learning_rate=0.03, n_estimators=300,
            subsample=0.8, colsample_bytree=0.8,
            tree_method="hist", n_jobs=-1, random_state=42, verbosity=0,
        ),
        X, y_home, y_away, seasons,
    )
    ph_ens = 0.5 * ridge[0] + 0.5 * xgb[0]
    pa_ens = 0.5 * ridge[1] + 0.5 * xgb[1]
    ens = report("集成：Ridge+XGBoost 等权平均", ph_ens, pa_ens, ridge[2], ridge[3], ridge[4] + xgb[4])

    # 加权集成（按验证表现给权重）
    ph_w = 0.75 * ridge[0] + 0.25 * xgb[0]
    pa_w = 0.75 * ridge[1] + 0.25 * xgb[1]
    report("集成：Ridge 0.75 + XGB 0.25", ph_w, pa_w, ridge[2], ridge[3], 0.0)

    logger.info("")
    logger.info("=" * 82)
    logger.info("结论")
    logger.info("=" * 82)
    logger.info(f"  线性基线 Ridge(alpha=1.0): 65.20%")
    all_acc = [(k, v["win_acc"]) for k, v in results.items()]
    best_new = max(all_acc, key=lambda x: x[1])
    logger.info(f"  本轮新增模型中最好: {best_new[0]} — {best_new[1]:.2%}")
    logger.info(f"  集合(等权) 胜率: {ens['win_acc']:.2%}")


if __name__ == "__main__":
    main()
