"""
赛季敏感性实验：某个赛季"去掉 vs 不去掉"对准确度的影响（走查式）。

实验 1: 留一赛季法（leave-one-season-out）
  预测赛季 S 时，训练集 = 所有 S 之前的赛季；逐个剔除其中的赛季 X，
  对比剔除 X 与不剔除的准确度变化，汇总每个 X 的平均影响。

实验 2: 时代相关性（只用近 N 个赛季训练）
  预测赛季 S 时，训练集分别用「全部历史赛季」和「最近 3 个赛季」，
  对比准确度——验证"时代进步后旧数据是否拖后腿"。

用法:
    python scripts/season_sensitivity.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts.backtest_seasons import TEST_SEASONS, load_all_games, mode_b_features

ALL_SEASONS = ["2016-17"] + TEST_SEASONS


def main():
    games = load_all_games()
    X, y_home, y_away, seasons, _, _ = mode_b_features(games)
    seasons_arr = np.array(seasons)

    # 实验 1: 留一赛季法
    logger.info("=" * 70)
    logger.info("实验 1: 留一赛季法——剔除某赛季对准确度的影响")
    logger.info("=" * 70)
    base_acc = {}
    per_delta = defaultdict(list)  # 被剔除赛季 X -> [(测试赛季 S, Δacc), ...]

    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        prior = [s for s in ALL_SEASONS if s < test_season]
        yh_te = y_home[test_mask]
        ya_te = y_away[test_mask]

        def fit_acc(tr_mask):
            scaler = StandardScaler()
            Xtr = scaler.fit_transform(X[tr_mask])
            Xte = scaler.transform(X[test_mask])
            mh = Ridge(alpha=1.0).fit(Xtr, y_home[tr_mask])
            ma = Ridge(alpha=1.0).fit(Xtr, y_away[tr_mask])
            ph = np.round(mh.predict(Xte)).astype(int)
            pa = np.round(ma.predict(Xte)).astype(int)
            return float(np.mean((ph > pa) == (yh_te > ya_te)))

        acc_all = fit_acc(train_mask)
        base_acc[test_season] = acc_all
        for dropped in prior:
            kept = train_mask & (seasons_arr != dropped)
            if kept.sum() < 100:
                continue
            acc_drop = fit_acc(kept)
            per_delta[dropped].append((test_season, acc_drop - acc_all))

    logger.info(f"{'被剔除赛季':<12}{'平均Δ准确度':>12}{'影响的测试赛季数':>14}{'明细':>30}")
    for dropped in ALL_SEASONS:
        entries = per_delta.get(dropped, [])
        if not entries:
            continue
        mean_d = np.mean([d for _, d in entries])
        detail = " ".join(f"{s}:{d:+.1%}" for s, d in entries)
        logger.info(f"{dropped:<12}{mean_d:>+11.2%}{len(entries):>14}{detail:>30}")

    # 实验 2: 只用近 3 个赛季训练
    logger.info("\n" + "=" * 70)
    logger.info("实验 2: 全历史训练 vs 只用最近 3 个赛季训练")
    logger.info("=" * 70)
    logger.info(f"{'测试赛季':<10}{'全历史':>9}{'近3赛季':>9}{'差异':>8}")
    for test_season in TEST_SEASONS:
        train_all = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_all.sum() < 100 or test_mask.sum() == 0:
            continue
        recent = [s for s in ALL_SEASONS if s < test_season][-3:]
        train_recent = train_all & np.array([s in recent for s in seasons])
        if train_recent.sum() < 100:
            continue
        yh_te = y_home[test_mask]
        ya_te = y_away[test_mask]

        def fit_acc(tr_mask):
            scaler = StandardScaler()
            Xtr = scaler.fit_transform(X[tr_mask])
            Xte = scaler.transform(X[test_mask])
            mh = Ridge(alpha=1.0).fit(Xtr, y_home[tr_mask])
            ma = Ridge(alpha=1.0).fit(Xtr, y_away[tr_mask])
            ph = np.round(mh.predict(Xte)).astype(int)
            pa = np.round(ma.predict(Xte)).astype(int)
            return float(np.mean((ph > pa) == (yh_te > ya_te)))

        a_all = fit_acc(train_all)
        a_recent = fit_acc(train_recent)
        logger.info(f"{test_season:<10}{a_all:>8.1%}{a_recent:>8.1%}{a_recent - a_all:>+7.2%}")


if __name__ == "__main__":
    main()
