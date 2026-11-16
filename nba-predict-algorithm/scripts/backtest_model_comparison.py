"""
多模型对比实验（走查式回测）

目的：在同一套特征、同一套时间划分下对比线性模型与树模型，
回答一个受控问题 —— 「准确率上不去，是模型瓶颈还是数据瓶颈？」

  · 树模型明显提升  → 模型瓶颈（线性模型捕捉不了特征交互）
  · 树模型也没有提升 → 数据瓶颈（信息量就这么多了）

公平性保证（缺一不可）：
  1. 所有模型使用完全相同的特征矩阵（mode_b_features，19 维）
  2. 所有模型使用完全相同的走查式训练/测试划分（TEST_SEASONS，9 折）
  3. 所有模型共享同一套 StandardScaler 拟合方式（每折只在训练集上 fit）
  4. 超参数固定并记录 —— 不做逐折调优，避免用测试集选参

两条建模路径（分开报告，不混）：
  路径 A：预测两队得分 → 分差 → sigmoid 转胜率（现生产路径）
  路径 B：直接二分类输出 P(主胜)（给不出比分）

评价指标：
  胜率准确率 / MAE总分 / MAE分差 / Brier分数（概率校准度）/ 训练耗时

用法:
    python scripts/backtest_model_comparison.py [--path A|B|both]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from scripts.backtest_seasons import TEST_SEASONS, load_all_games, mode_b_features

# 预测分差 → 胜率的尺度参数（与生产一致）
SIGMOID_SCALE = 7.0

try:
    from xgboost import XGBClassifier, XGBRegressor
    HAS_XGB = True
except ImportError:  # pragma: no cover
    HAS_XGB = False


# ---------- 模型定义（超参数固定并记录，便于复现） ----------

def regression_models() -> dict:
    """路径 A：回归模型，预测主客队得分"""
    m = {
        "OLS 线性回归(无正则)": lambda: LinearRegression(),
        "Ridge (alpha=0.01)": lambda: Ridge(alpha=0.01),
        "Ridge (alpha=1.0)": lambda: Ridge(alpha=1.0),
        "随机森林 (n=300, leaf=2)": lambda: RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=42
        ),
        "梯度提升树 GBDT (n=200, lr=0.05, depth=4)": lambda: GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
        ),
    }
    if HAS_XGB:
        m["XGBoost (n=300, lr=0.05, depth=6)"] = lambda: XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            tree_method="hist", n_jobs=-1, random_state=42, verbosity=0,
        )
    return m


def classification_models() -> dict:
    """路径 B：二分类模型，直接输出 P(主胜)"""
    m = {
        "逻辑回归 (L2)": lambda: LogisticRegression(max_iter=1000, C=1.0),
        "随机森林分类 (n=300, leaf=2)": lambda: RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=42
        ),
    }
    if HAS_XGB:
        m["XGBoost 分类 (n=300, lr=0.05, depth=6)"] = lambda: XGBClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            tree_method="hist", n_jobs=-1, random_state=42,
            verbosity=0, eval_metric="logloss",
        )
    return m


# ---------- 指标 ----------

def sigmoid_from_diff(diff):
    return 1.0 / (1.0 + np.exp(-np.asarray(diff, dtype=float) / SIGMOID_SCALE))


def metrics(y_home, y_away, pred_h, pred_a, y_win, p_home):
    n = len(y_home)
    mae_total = float(np.mean(np.abs(pred_h + pred_a - y_home - y_away)))
    mae_diff = float(np.mean(np.abs((pred_h - pred_a) - (y_home - y_away))))
    win_acc = float(np.mean((pred_h > pred_a) == (y_home > y_away)))
    brier = float(np.mean((p_home - y_win) ** 2))
    return {"n": n, "win_acc": win_acc, "mae_total": mae_total,
            "mae_diff": mae_diff, "brier": brier}


# ---------- 走查式回测 ----------

def walk_regression(model_factory, X, y_home, y_away, seasons, playoffs):
    """路径 A：每折训练主/客两个回归模型"""
    seasons_arr = np.array(seasons)
    yh_all, ya_all, ph_all, pa_all, po_all = [], [], [], [], []
    train_seconds = 0.0

    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])

        t0 = time.perf_counter()
        m_h = model_factory().fit(X_tr, y_home[train_mask])
        m_a = model_factory().fit(X_tr, y_away[train_mask])
        train_seconds += time.perf_counter() - t0

        ph_all.append(m_h.predict(X_te))
        pa_all.append(m_a.predict(X_te))
        yh_all.append(y_home[test_mask])
        ya_all.append(y_away[test_mask])
        po_all.append(playoffs[test_mask])

    yh = np.concatenate(yh_all)
    ya = np.concatenate(ya_all)
    ph = np.concatenate(ph_all)
    pa = np.concatenate(pa_all)
    y_win = (yh > ya).astype(float)
    return metrics(yh, ya, ph, pa, y_win, sigmoid_from_diff(ph - pa)), train_seconds


def walk_classification(model_factory, X, y_home, y_away, seasons, playoffs):
    """路径 B：每折训练一个二分类模型，直接输出 P(主胜)"""
    seasons_arr = np.array(seasons)
    y_win_all = (y_home > y_away).astype(int)
    yh_all, ya_all, p_all = [], [], []
    train_seconds = 0.0

    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])

        t0 = time.perf_counter()
        model = model_factory().fit(X_tr, y_win_all[train_mask])
        train_seconds += time.perf_counter() - t0

        p_all.append(model.predict_proba(X_te)[:, 1])
        yh_all.append(y_home[test_mask])
        ya_all.append(y_away[test_mask])

    yh = np.concatenate(yh_all)
    ya = np.concatenate(ya_all)
    p = np.concatenate(p_all)
    y_win = (yh > ya).astype(float)
    # 路径 B 给不出比分，比分类指标记为 nan
    return {"n": len(yh),
            "win_acc": float(np.mean((p > 0.5) == (y_win > 0.5))),
            "mae_total": float("nan"), "mae_diff": float("nan"),
            "brier": float(np.mean((p - y_win) ** 2))}, train_seconds


# ---------- 主流程 ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", choices=["A", "B", "both"], default="both")
    args = parser.parse_args()

    games = load_all_games()
    X, y_home, y_away, seasons, playoffs, feat_names = mode_b_features(games)
    X = np.asarray(X, dtype=float)
    logger.info(f"样本 {len(X)} 场, 特征 {X.shape[1]} 维, 走查折数 {len(TEST_SEASONS)}")

    home_baseline = float(np.mean(y_home > y_away))
    logger.info(f"基线（猜主队）: {home_baseline:.2%}\n")

    header = f"{'模型':<34}{'胜率':>9}{'MAE总分':>10}{'MAE分差':>10}{'Brier':>9}{'训练(s)':>9}"

    rows = []

    if args.path in ("A", "both"):
        logger.info("=" * 82)
        logger.info("路径 A：预测两队得分 → 分差 → sigmoid 转胜率（现生产路径）")
        logger.info("=" * 82)
        logger.info(header)
        logger.info("-" * 82)
        for name, factory in regression_models().items():
            m, secs = walk_regression(factory, X, y_home, y_away, seasons, playoffs)
            rows.append(("A", name, m, secs))
            logger.info(f"{name:<34}{m['win_acc']:>9.2%}{m['mae_total']:>10.2f}"
                        f"{m['mae_diff']:>10.2f}{m['brier']:>9.4f}{secs:>9.1f}")
        logger.info("")

    if args.path in ("B", "both"):
        logger.info("=" * 82)
        logger.info("路径 B：直接二分类输出 P(主胜)（给不出比分）")
        logger.info("=" * 82)
        logger.info(header)
        logger.info("-" * 82)
        for name, factory in classification_models().items():
            m, secs = walk_classification(factory, X, y_home, y_away, seasons, playoffs)
            rows.append(("B", name, m, secs))
            logger.info(f"{name:<34}{m['win_acc']:>9.2%}{'—':>10}{'—':>10}"
                        f"{m['brier']:>9.4f}{secs:>9.1f}")
        logger.info("")

    # 汇总：谁赢，赢多少
    if rows:
        logger.info("=" * 82)
        logger.info("结论摘要")
        logger.info("=" * 82)
        best = max(rows, key=lambda r: r[2]["win_acc"])
        ridge_a = next((r for r in rows if r[0] == "A" and "Ridge (alpha=0.01)" in r[1]), None)
        logger.info(f"  最优模型: [{best[0]}路径] {best[1]} — 胜率 {best[2]['win_acc']:.2%}")
        if ridge_a:
            delta = best[2]["win_acc"] - ridge_a[2]["win_acc"]
            logger.info(f"  相对 Ridge(α=0.01) 基线 {ridge_a[2]['win_acc']:.2%}: {delta:+.2%}")
            if abs(delta) < 0.005:
                logger.info("  → 差距 < 0.5 个百分点：倾向「数据瓶颈」，换模型收益有限")
            elif delta > 0:
                logger.info("  → 树模型有提升：倾向「模型瓶颈」，线性模型捕捉不到特征交互")
            else:
                logger.info("  → 树模型反而更差：线性模型在此任务上更稳")
        logger.info(f"  基线（猜主队）: {home_baseline:.2%}")


if __name__ == "__main__":
    main()
