"""
XGBoost 超参数网格搜索（走查式回测，与模型对比实验同一套划分）

目的：排除「树模型之所以落后是因为没调参」这一可能，使对比结论站得住。

方法论说明（重要）：
    本脚本在**全部走查折的合并结果**上挑选最优超参数 —— 严格来说这已构成
    轻度测试集污染。这里**故意这么做**：等于给 XGBoost 开了后门、给它最好的机会。
    若在「事后最优参数」下仍无法追平线性模型，则「树模型不适配本任务」的
    结论是稳健的（对树模型最有利的设定都输了）。

用法:
    python scripts/tune_xgb_grid.py
"""
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from xgboost import XGBRegressor

from scripts.backtest_model_comparison import walk_regression
from scripts.backtest_seasons import load_all_games, mode_b_features

# 线性模型基线（来自 backtest_model_comparison.py，16 维特征集）
RIDGE_BASELINE = 0.6521

GRID = {
    "max_depth": [3, 4, 6],
    "learning_rate": [0.03, 0.05, 0.1],
    "n_estimators": [300, 800],
}


def main():
    games = load_all_games()
    X, y_home, y_away, seasons, playoffs, _ = mode_b_features(games)
    X = np.asarray(X, dtype=float)

    combos = list(itertools.product(
        GRID["max_depth"], GRID["learning_rate"], GRID["n_estimators"]
    ))
    logger.info(f"网格组合 {len(combos)} 个，样本 {len(X)} 场，走查 9 折")
    logger.info(f"线性模型基线（Ridge α=1.0）: {RIDGE_BASELINE:.2%}\n")
    logger.info(f"{'max_depth':>10}{'lr':>7}{'n_est':>7}{'胜率':>10}{'MAE总分':>10}{'Brier':>9}{'耗时(s)':>9}")
    logger.info("-" * 62)

    results = []
    t_all = time.perf_counter()
    for depth, lr, n_est in combos:
        factory = lambda d=depth, l=lr, n=n_est: XGBRegressor(
            max_depth=d, learning_rate=l, n_estimators=n,
            subsample=0.8, colsample_bytree=0.8,
            tree_method="hist", n_jobs=-1, random_state=42, verbosity=0,
        )
        m, secs = walk_regression(factory, X, y_home, y_away, seasons, playoffs)
        results.append(((depth, lr, n_est), m, secs))
        logger.info(f"{depth:>10}{lr:>7}{n_est:>7}{m['win_acc']:>10.2%}"
                    f"{m['mae_total']:>10.2f}{m['brier']:>9.4f}{secs:>9.1f}")

    logger.info("-" * 62)
    logger.info(f"总耗时 {time.perf_counter() - t_all:.0f}s\n")

    best_params, best_m, _ = max(results, key=lambda r: r[1]["win_acc"])
    logger.info("=" * 62)
    logger.info("结论")
    logger.info("=" * 62)
    logger.info(f"  调参后最优 XGBoost: depth={best_params[0]} lr={best_params[1]} "
                f"n_est={best_params[2]} → 胜率 {best_m['win_acc']:.2%}")
    logger.info(f"  线性模型基线 (Ridge α=1.0)     → 胜率 {RIDGE_BASELINE:.2%}")
    delta = best_m["win_acc"] - RIDGE_BASELINE
    logger.info(f"  差距: {delta:+.2%}")
    if delta < 0:
        logger.info("  → 即使在事后最优参数下，XGBoost 仍落后线性模型。")
        logger.info("    「树模型不适配本任务」的结论成立（已给树模型最有利的设定）")
    else:
        logger.info("  → 调参后 XGBoost 追平/反超，原对比结论需要修正")

    # 各 depth / lr 的趋势，便于分析
    logger.info("")
    logger.info("按 max_depth 分组的最优胜率:")
    for d in GRID["max_depth"]:
        sub = [r for r in results if r[0][0] == d]
        b = max(sub, key=lambda r: r[1]["win_acc"])
        logger.info(f"  depth={d}: {b[1]['win_acc']:.2%}  (lr={b[0][1]}, n_est={b[0][2]})")


if __name__ == "__main__":
    main()
