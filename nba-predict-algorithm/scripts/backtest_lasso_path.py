"""
Lasso 正则化路径实验：准确率 vs 保留特征数

目的：验证「现有 19 维特征里有多少是冗余的」。
做法：逐步增大 L1 惩罚 alpha，观察
  · Lasso 自动归零多少个特征
  · 走查式回测下的准确率如何变化（用与主实验完全相同的 9 折划分）

补充：用 Ridge 在「去掉 Lasso 归零特征后的子集」上重跑一次，
直接检验「冗余特征能否安全删除」。

用法:
    python scripts/backtest_lasso_path.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.linear_model import Lasso, Ridge
from sklearn.preprocessing import StandardScaler

from scripts.backtest_seasons import TEST_SEASONS, load_all_games, mode_b_features

ALPHAS = [0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
SIGMOID_SCALE = 7.0


def walk_eval(make_model, X, y_home, y_away, seasons, cols=None):
    """走查式回测，返回 (胜率, MAE总分, MAE分差, Brier)"""
    seasons_arr = np.array(seasons)
    yh_all, ya_all, ph_all, pa_all = [], [], [], []
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        X_use = X if cols is None else X[:, cols]
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_use[train_mask])
        X_te = scaler.transform(X_use[test_mask])
        m_h = make_model().fit(X_tr, y_home[train_mask])
        m_a = make_model().fit(X_tr, y_away[train_mask])
        ph_all.append(m_h.predict(X_te))
        pa_all.append(m_a.predict(X_te))
        yh_all.append(y_home[test_mask])
        ya_all.append(y_away[test_mask])

    yh, ya = np.concatenate(yh_all), np.concatenate(ya_all)
    ph, pa = np.concatenate(ph_all), np.concatenate(pa_all)
    y_win = (yh > ya).astype(float)
    p = 1.0 / (1.0 + np.exp(-(ph - pa) / SIGMOID_SCALE))
    return {
        "win_acc": float(np.mean((ph > pa) == (yh > ya))),
        "mae_total": float(np.mean(np.abs(ph + pa - yh - ya))),
        "mae_diff": float(np.mean(np.abs((ph - pa) - (yh - ya)))),
        "brier": float(np.mean((p - y_win) ** 2)),
    }


def main():
    games = load_all_games()
    X, y_home, y_away, seasons, playoffs, names = mode_b_features(games)
    X = np.asarray(X, dtype=float)
    names = list(names)
    n_feat = X.shape[1]
    logger.info(f"样本 {len(X)} 场, 特征 {n_feat} 维\n")

    # 全量标准化（仅用于观察归零特征，不用于评估）
    Xs_full = StandardScaler().fit_transform(X)

    logger.info(f"{'alpha':>7}{'归零':>6}{'保留':>6}{'胜率':>9}{'MAE总分':>10}{'Brier':>9}")
    logger.info("-" * 50)

    rows = []
    zeroed_at = {}
    for a in ALPHAS:
        m = Lasso(alpha=a, max_iter=50000).fit(Xs_full, y_home)
        zeroed = [n for n, c in zip(names, m.coef_) if abs(c) < 1e-8]
        zeroed_at[a] = zeroed

        r = walk_eval(lambda a=a: Lasso(alpha=a, max_iter=50000),
                      X, y_home, y_away, seasons)
        rows.append((a, len(zeroed), r))
        logger.info(f"{a:>7}{len(zeroed):>6}{n_feat - len(zeroed):>6}"
                    f"{r['win_acc']:>9.2%}{r['mae_total']:>10.2f}{r['brier']:>9.4f}")

    logger.info("")
    logger.info("各 alpha 下被归零的特征:")
    prev = set()
    for a in ALPHAS:
        cur = set(zeroed_at[a])
        newly = cur - prev
        if newly:
            logger.info(f"  alpha={a}: 新增归零 {sorted(newly)}")
        prev = cur

    # 补充检验：直接删掉 alpha=0.01 时归零的 5 个特征，用 Ridge 重跑
    drop = zeroed_at[ALPHAS[0]]
    keep_cols = [i for i, n in enumerate(names) if n not in drop]
    logger.info("")
    logger.info(f"补充检验：删掉 alpha=0.01 归零的 {len(drop)} 个特征（{drop}）")
    logger.info("         在剩余 {} 维上用 Ridge(alpha=1.0) 重跑".format(len(keep_cols)))
    ridge_full = walk_eval(lambda: Ridge(alpha=1.0), X, y_home, y_away, seasons)
    ridge_sub = walk_eval(lambda: Ridge(alpha=1.0), X, y_home, y_away, seasons, keep_cols)
    logger.info(f"  全部 {n_feat} 维: 胜率 {ridge_full['win_acc']:.2%}, MAE总分 {ridge_full['mae_total']:.2f}")
    logger.info(f"  仅 {len(keep_cols):>2} 维: 胜率 {ridge_sub['win_acc']:.2%}, MAE总分 {ridge_sub['mae_total']:.2f}")
    delta = ridge_sub["win_acc"] - ridge_full["win_acc"]
    logger.info(f"  差值: {delta:+.2%}")

    logger.info("")
    logger.info("=" * 50)
    logger.info("结论")
    logger.info("=" * 50)
    best = max(rows, key=lambda r: r[2]["win_acc"])
    logger.info(f"  最优 alpha={best[0]}（保留 {n_feat - best[1]} 维）→ 胜率 {best[2]['win_acc']:.2%}")
    logger.info(f"  基线 Ridge(alpha=1.0) 全 {n_feat} 维 → 胜率 {ridge_full['win_acc']:.2%}")


if __name__ == "__main__":
    main()
