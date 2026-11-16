"""
Ridge 模型训练 v3 —— 对齐无泄漏的 Mode B 特征集（19 维）

背景：
    v2 模型（ridge_model.json）使用 30 维特征，其中包含 team_data 的赛季汇总数据
    （off_rating / eFG% / TS% / AST% 等）。回测时这些汇总量会泄漏未来信息。

    v3 改用 Mode B 的 19 维特征 —— 全部可以由「该场之前的比赛比分」推导，
    与 backtest_model_comparison.py / backtest_lasso_path.py 的实验口径完全一致。

    证据：在 19 维特征集上做了 20 个模型的对比实验，
    线性模型 65.20% 为最优，树模型全部落后（63.51% 至 59.67%）。

训练口径：
    · 特征：mode_b_features（时点安全，无泄漏）
    · 样本：全部 10 个赛季中通过冷启动门槛的比赛（约 12,062 场）
    · 模型：Ridge(alpha=1.0)，与对比实验中的最优线性配置一致
    · 报告的验证指标取自走查式回测（9 折），而非训练集拟合值

用法:
    python scripts/train_model_ridge_v3.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts.backtest_seasons import FEATURE_NAMES_B, load_all_games, mode_b_features

ALPHA = 1.0
MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "ridge_model.json"

# 走查式回测结果（来自 backtest_model_comparison.py，同一套 16 维特征与划分）
WALKFORWARD_WIN_ACC = 0.6521
WALKFORWARD_MAE_TOTAL = 15.05
# 回测残差的标准差，用于给出预测区间（±1σ 约覆盖 68% 的比赛）
WALKFORWARD_STD_TOTAL = 18.84
WALKFORWARD_STD_DIFF = 13.85


def main():
    games = load_all_games()
    X, y_home, y_away, seasons, playoffs, names = mode_b_features(games)
    X = np.asarray(X, dtype=float)
    names = list(names)
    logger.info(f"样本 {len(X)} 场, 特征 {X.shape[1]} 维, 赛季 {seasons[0]} ~ {seasons[-1]}")

    assert names == FEATURE_NAMES_B, "特征顺序与 Mode B 定义不一致"

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    m_home = Ridge(alpha=ALPHA).fit(Xs, y_home)
    m_away = Ridge(alpha=ALPHA).fit(Xs, y_away)
    logger.info(f"训练完成: alpha={ALPHA}")

    # 训练集内拟合值（仅作参考，不是泛化指标）
    insample_acc = float(np.mean((m_home.predict(Xs) > m_away.predict(Xs)) == (y_home > y_away)))
    logger.info(f"训练集内拟合准确率 {insample_acc:.2%}（参考值，非泛化指标）")

    model = {
        "model_type": "ridge_regression",
        "version": "ridge_v3_mode_b",
        "feature_set": "mode_b_19 (时点安全，无数据泄漏)",
        "features": names,
        "alpha": ALPHA,
        "home_coefficients": {n: round(float(c), 4) for n, c in zip(names, m_home.coef_)},
        "away_coefficients": {n: round(float(c), 4) for n, c in zip(names, m_away.coef_)},
        "home_intercept": round(float(m_home.intercept_), 2),
        "away_intercept": round(float(m_away.intercept_), 2),
        "scaler_mean": {n: round(float(v), 4) for n, v in zip(names, scaler.mean_)},
        "scaler_scale": {n: round(float(v), 4) for n, v in zip(names, scaler.scale_)},
        "training_samples": int(len(X)),
        "training_seasons": f"{seasons[0]} ~ {seasons[-1]}",
        "validation_win_acc": WALKFORWARD_WIN_ACC,
        "validation_mae_total": WALKFORWARD_MAE_TOTAL,
        "residual_std_total": WALKFORWARD_STD_TOTAL,
        "residual_std_diff": WALKFORWARD_STD_DIFF,
        "validation_method": "走查式回测（9 折，预测赛季 S 只用 S 之前的数据训练）",
    }

    MODEL_PATH.write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"已写入 {MODEL_PATH}")

    # 系数绝对值排名，便于人工核对合理性
    coef_abs = sorted(
        ((n, abs(float(c))) for n, c in zip(names, m_home.coef_)),
        key=lambda x: x[1], reverse=True,
    )
    logger.info("主队模型系数绝对值 Top 10:")
    for n, v in coef_abs[:10]:
        logger.info(f"  {n:<24}{v:>8.3f}")


if __name__ == "__main__":
    main()
