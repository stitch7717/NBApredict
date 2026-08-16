"""
基线对照：永远押强队 vs 模型 vs 永远猜主队

"强队"定义：时点口径（只用该场比赛之前的比赛）滚动胜率更高的一方。
与 backtest_seasons.py 模式 B 使用同一套滚动状态，公平对比。

用法:
    python scripts/baseline_favorite.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts.backtest_seasons import (
    TEST_SEASONS, load_all_games, mode_b_features,
)


def favorite_predictions(games: list):
    """
    为每场比赛生成"押强队"预测（时点滚动胜率），
    返回对齐 mode_b_features 样本的 (season, playoff, y_home, y_away, fav_home_win)。
    """
    # 与 mode_b_features 相同的滚动状态
    acc = defaultdict(lambda: {"wins": 0, "losses": 0})
    results = []
    for g in games:
        hk = (g["home_team_id"], g["season"])
        ak = (g["away_team_id"], g["season"])
        h, a = acc[hk], acc[ak]
        if (h["wins"] + h["losses"]) >= 5 and (a["wins"] + a["losses"]) >= 5:
            h_wp = h["wins"] / (h["wins"] + h["losses"])
            a_wp = a["wins"] / (a["wins"] + a["losses"])
            # 押强队：预测胜率更高一方赢（平局按主队）
            fav_home_win = 1 if h_wp >= a_wp else 0
            results.append((g["season"], g["is_playoff"], g["home_score"], g["away_score"], fav_home_win))
        # 滚动状态更新（本场结果只在之后可见）
        hs, as_ = g["home_score"], g["away_score"]
        for key, pf, pa in ((hk, hs, as_), (ak, as_, hs)):
            s = acc[key]
            if pf > pa:
                s["wins"] += 1
            else:
                s["losses"] += 1
    return results


def acc_of(rows):
    n = len(rows)
    if n == 0:
        return None
    correct = sum(1 for _, _, yh, ya, fav_home in rows if (yh > ya) == bool(fav_home))
    return {"n": n, "acc": correct / n}


def main():
    games = load_all_games()
    logger.info(f"共 {len(games)} 场比赛")

    fav_rows = favorite_predictions(games)
    logger.info(f"押强队基线样本: {len(fav_rows)} 场")

    # 模型 B 模式预测（复用回测逻辑）
    X, y_home, y_away, seasons, playoffs, _ = mode_b_features(games)
    seasons_arr = np.array(seasons)
    model_rows = {}
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])
        m_home = Ridge(alpha=1.0).fit(X_tr, y_home[train_mask])
        m_away = Ridge(alpha=1.0).fit(X_tr, y_away[train_mask])
        ph = np.round(m_home.predict(X_te)).astype(int)
        pa = np.round(m_away.predict(X_te)).astype(int)
        model_rows[test_season] = (y_home[test_mask], y_away[test_mask], (ph > pa).astype(int), playoffs[test_mask])

    logger.info(f"{'赛季':<10}{'强队胜率':>12}{'模型胜率':>12}{'猜主队':>12}{'场次':>8}")
    lines = []
    for season in TEST_SEASONS:
        s_rows = [r for r in fav_rows if r[0] == season]
        fav = acc_of(s_rows)
        m = model_rows.get(season)
        if not m or not fav:
            continue
        yh, ya, pred, po = m
        model_acc = float(np.mean(pred == (yh > ya)))
        home_acc = float(np.mean(yh > ya))
        logger.info(f"{season:<10}{fav['acc']:>11.1%}{model_acc:>11.1%}{home_acc:>11.1%}{fav['n']:>8}")
        lines.append(f"{season:<10}{fav['acc']:>11.1%}{model_acc:>11.1%}{home_acc:>11.1%}{fav['n']:>8}")

    # 汇总
    all_fav = acc_of(fav_rows)
    yh_all = np.concatenate([m[0] for m in model_rows.values()])
    ya_all = np.concatenate([m[1] for m in model_rows.values()])
    pred_all = np.concatenate([m[2] for m in model_rows.values()])
    model_all = float(np.mean(pred_all == (yh_all > ya_all)))
    home_all = float(np.mean(yh_all > ya_all))
    logger.info("-" * 50)
    logger.info(f"{'汇总':<10}{all_fav['acc']:>11.1%}{model_all:>11.1%}{home_all:>11.1%}{all_fav['n']:>8}")
    lines.append(f"{'汇总':<10}{all_fav['acc']:>11.1%}{model_all:>11.1%}{home_all:>11.1%}{all_fav['n']:>8}")

    report = Path(__file__).resolve().parent.parent / "logs" / "baseline_favorite.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"报告: {report}")


if __name__ == "__main__":
    main()
