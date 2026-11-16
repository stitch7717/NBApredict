"""
特征体系逐层消融实验（走查式，预测赛季 S 只用 S 之前数据）

目的：量化每一层特征设计的边际贡献，回答"特征工程带来多少提升"。

层级（累积式）：
  L1 基础得分      : 两队场均得分/失分                        (4 维)
  L2 +赛季战绩     : 胜率                                     (6 维)
  L3 +近期状态     : 近 10 场胜率 + 动量                      (10 维)
  L4 +净效率与节奏 : 净效率、节奏                              (14 维)
  L5 +主客场差分   : 主客场得分差                              (15 维)
  L6 +场景         : 季后赛标志                                (16 维)
  L7 +市场信息     : 让分线、大小分线                          (18 维)

用法:
    python scripts/backtest_feature_ablation.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.db.database import SessionLocal
from app.db.models import OddsData
from scripts.backtest_seasons import MIN_PRIOR_GAMES, TEST_SEASONS, load_all_games, mode_b_features

ALPHA = 1.0

# 各层级的列索引（累积）
LAYERS = [
    ("L1 基础得分", [0, 1, 2, 3]),
    ("L2 +赛季战绩", [4, 5]),
    ("L3 +近期状态", [6, 7, 14, 15]),
    ("L4 +净效率节奏", [8, 9, 10, 11]),
    ("L5 +主客场差分", [12]),
    ("L6 +场景标志", [13]),
]


def build_odds_arrays(sample_ids):
    with SessionLocal() as db:
        rows = db.query(OddsData).all()
    diff_map, total_map = {}, {}
    for o in rows:
        if o.handicap_line is not None:
            diff_map[o.game_id] = -o.handicap_line
        if o.total_line is not None:
            total_map[o.game_id] = o.total_line
    md = np.array([diff_map.get(g, 0.0) for g in sample_ids], dtype=float)
    mt = np.array([total_map.get(g, 210.0) for g in sample_ids], dtype=float)
    has = np.array([(g in diff_map) or (g in total_map) for g in sample_ids])
    return md, mt, has


def walk_eval(X, y_home, y_away, seasons):
    """走查式：每个测试赛季用其之前的赛季训练，返回 (场次, 胜率, MAE总分)"""
    seasons_arr = np.array(seasons)
    hits = n = 0
    mae_sum = 0.0
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        scaler = StandardScaler().fit(X[train_mask])
        model_h = Ridge(alpha=ALPHA).fit(scaler.transform(X[train_mask]), y_home[train_mask])
        model_a = Ridge(alpha=ALPHA).fit(scaler.transform(X[train_mask]), y_away[train_mask])
        Xt = scaler.transform(X[test_mask])
        ph, pa = model_h.predict(Xt), model_a.predict(Xt)
        yh, ya = y_home[test_mask], y_away[test_mask]
        hits += int(np.sum((ph > pa) == (yh > ya)))
        n += int(test_mask.sum())
        mae_sum += float(np.sum(np.abs((ph + pa) - (yh + ya))))
    return n, hits / max(n, 1), mae_sum / max(n, 1)


def main():
    games = load_all_games()
    logger.info(f"总比赛: {len(games)}")

    # 样本对齐（与其它回测同口径）
    sample_ids = []
    acc = defaultdict(lambda: {"wins": 0, "losses": 0})
    for g in games:
        hk = (g["home_team_id"], g["season"])
        ak = (g["away_team_id"], g["season"])
        h, a = acc[hk], acc[ak]
        if (h["wins"] + h["losses"]) >= MIN_PRIOR_GAMES and (a["wins"] + a["losses"]) >= MIN_PRIOR_GAMES:
            sample_ids.append(g["game_id"])
        for key, pf, pa in ((hk, g["home_score"], g["away_score"]),
                            (ak, g["away_score"], g["home_score"])):
            s = acc[key]
            if pf > pa:
                s["wins"] += 1
            else:
                s["losses"] += 1

    X, y_home, y_away, seasons, playoffs, feat_names = mode_b_features(games)
    assert len(sample_ids) == len(X), f"对齐失败 {len(sample_ids)} vs {len(X)}"
    logger.info(f"样本: {len(X)} 场, 基础特征 {X.shape[1]} 维")

    md, mt, has_odds = build_odds_arrays(sample_ids)
    logger.info(f"有赔率的样本: {int(has_odds.sum())} / {len(has_odds)}")
    X = np.column_stack([X, md, mt])

    logger.info(f"\n{'层级':<16}{'维度':>6}{'胜率':>10}{'较上层':>10}{'MAE总分':>10}")
    logger.info("-" * 56)

    cols, prev_acc, prev_name = [], None, ""
    rows = []
    for name, idx in LAYERS:
        cols.extend(idx)
        n, acc_, mae = walk_eval(X[:, cols], y_home, y_away, seasons)
        delta = "" if prev_acc is None else f"{acc_ - prev_acc:+.2%}"
        logger.info(f"{name:<16}{len(cols):>6}{acc_:>10.2%}{delta:>10}{mae:>10.2f}")
        rows.append((name, len(cols), acc_, mae))
        prev_acc = acc_
        prev_name = name

    # 加赔率层（仅在同时有赔率的子集上评估，保证可比）
    n, acc_odds, mae_odds = walk_eval(X[:, cols + [16, 17]], y_home, y_away, seasons)
    logger.info(f"{'L7 +市场信息':<16}{len(cols) + 2:>6}{acc_odds:>10.2%}{acc_odds - prev_acc:>+10.2%}{mae_odds:>10.2f}")

    logger.info("-" * 56)
    logger.info(f"\n关键结论：")
    logger.info(f"  L1 基础得分 → L6 完整特征: {rows[0][2]:.2%} → {rows[-1][2]:.2%} "
                f"（特征工程净贡献 {rows[-1][2] - rows[0][2]:+.2%}）")
    logger.info(f"  L6 完整特征 → L7 加市场信息: {rows[-1][2]:.2%} → {acc_odds:.2%} "
                f"（多源融合净贡献 {acc_odds - rows[-1][2]:+.2%}）")


if __name__ == "__main__":
    main()
