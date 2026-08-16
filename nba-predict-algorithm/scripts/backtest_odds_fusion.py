"""
赔率校准/融合实验：验证赔率数据能提升多少模型准确度（非下注视角）。

三组对照（全部走查式，预测赛季 S 只用 S 之前的数据）:
  A. 基线: mode B 特征（65.1%）
  B. 赔率特征进模型: B 特征 + 市场分差(-让分线) + 市场总分(大小分线)
  C. 预测融合: 模型预测分差/总分与市场线加权平均，权重 w 在训练集上网格调优
     fused_diff = (1-w)*model_diff + w*market_diff, 按符号判胜负

说明: 用收盘线作特征测得的是"上限"（收盘线在开球前才最终确定）；
生产环境可用赛前盘（okooo 竞彩）近似，融合逻辑不变。

用法:
    python scripts/backtest_odds_fusion.py
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

W_GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def build_odds_features():
    """每场赔率特征: (market_diff, market_total)，与 game_id 对齐"""
    with SessionLocal() as db:
        rows = db.query(OddsData).all()
    diff_map = {}
    total_map = {}
    for o in rows:
        if o.handicap_line is not None:
            diff_map[o.game_id] = -o.handicap_line  # 市场预测的分差（主队视角）
        if o.total_line is not None:
            total_map[o.game_id] = o.total_line
    return diff_map, total_map


def walk_predictions(X, y_home, y_away, seasons, extra=None):
    """走查返回每测试赛季的 (test_pos, ph, pa, yh, ya, extras_test)"""
    seasons_arr = np.array(seasons)
    out = {}
    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        if extra is not None:
            X_all = np.hstack([X, extra])
        else:
            X_all = X
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_all[train_mask])
        X_te = scaler.transform(X_all[test_mask])
        m_home = Ridge(alpha=1.0).fit(X_tr, y_home[train_mask])
        m_away = Ridge(alpha=1.0).fit(X_tr, y_away[train_mask])
        ph = np.round(m_home.predict(X_te)).astype(int)
        pa = np.round(m_away.predict(X_te)).astype(int)
        ph_tr = np.round(m_home.predict(X_tr)).astype(int)  # 训练集内预测（供融合调优）
        pa_tr = np.round(m_away.predict(X_tr)).astype(int)
        out[test_season] = {
            "train_mask": train_mask, "test_mask": test_mask,
            "ph": ph, "pa": pa,
            "ph_tr": ph_tr, "pa_tr": pa_tr,
            "yh": y_home[test_mask], "ya": y_away[test_mask],
        }
    return out


def win_acc(ph, pa, yh, ya) -> float:
    return float(np.mean((ph > pa) == (yh > ya)))


def main():
    games = load_all_games()
    diff_map, total_map = build_odds_features()

    # 样本对齐（mode B 的口径）
    sample_ids = []
    acc = defaultdict(lambda: {"wins": 0, "losses": 0})
    for g in games:
        hk = (g["home_team_id"], g["season"])
        ak = (g["away_team_id"], g["season"])
        h, a = acc[hk], acc[ak]
        if (h["wins"] + h["losses"]) >= MIN_PRIOR_GAMES and (a["wins"] + a["losses"]) >= MIN_PRIOR_GAMES:
            sample_ids.append(g["game_id"])
        hs, as_ = g["home_score"], g["away_score"]
        for key, pf, pa in ((hk, hs, as_), (ak, as_, hs)):
            s = acc[key]
            if pf > pa:
                s["wins"] += 1
            else:
                s["losses"] += 1

    X, y_home, y_away, seasons, _, _ = mode_b_features(games)
    assert len(sample_ids) == len(X)
    md = np.array([diff_map.get(gid, 0.0) for gid in sample_ids], dtype=float)
    mt = np.array([total_map.get(gid, 210.0) for gid in sample_ids], dtype=float)
    has_diff = np.array([gid in diff_map for gid in sample_ids])
    has_total = np.array([gid in total_map for gid in sample_ids])

    # A: 基线
    res_a = walk_predictions(X, y_home, y_away, seasons)
    # B: 赔率特征进模型
    res_b = walk_predictions(X, y_home, y_away, seasons, extra=np.column_stack([md, mt]))

    logger.info(f"{'赛季':<10}{'A基线':>9}{'B赔率特征':>11}{'C融合调优':>11}{'融合w':>7}{'盘口':>8}")
    lines = []
    total_n = {"A": 0, "B": 0, "C": 0}
    total_hit = {"A": 0, "B": 0, "C": 0}
    for season in TEST_SEASONS:
        if season not in res_a:
            continue
        r = res_a[season]
        r_b = res_b[season]
        test_mask = r["test_mask"]

        acc_a = win_acc(r["ph"], r["pa"], r["yh"], r["ya"])
        acc_b = win_acc(r_b["ph"], r_b["pa"], r_b["yh"], r_b["ya"])

        # C: 融合，w 在训练集调优（用训练集内预测）
        best_w, best_acc = 0.0, 0.0
        for w in W_GRID:
            fused_train = (1 - w) * (r_b["ph_tr"] - r_b["pa_tr"]) + w * md[r["train_mask"]]
            tr_acc = float(np.mean((fused_train > 0) == (y_home[r["train_mask"]] > y_away[r["train_mask"]])))
            if tr_acc > best_acc:
                best_acc, best_w = tr_acc, w
        fused_test = (1 - best_w) * (r_b["ph"] - r_b["pa"]) + best_w * md[test_mask]
        acc_c = float(np.mean((fused_test > 0) == (r["yh"] > r["ya"])))

        # 盘口单独命中（同集）
        market_test = md[test_mask]
        acc_mkt = float(np.mean((market_test > 0) == (r["yh"] > r["ya"])))

        n = len(r["ph"])
        logger.info(f"{season:<10}{acc_a:>8.1%}{acc_b:>10.1%}{acc_c:>10.1%}{best_w:>7.2f}{acc_mkt:>7.1%}")
        lines.append(f"{season:<10}{acc_a:>8.1%}{acc_b:>10.1%}{acc_c:>10.1%}{best_w:>7.2f}{acc_mkt:>7.1%}")
        for k, v in (("A", acc_a), ("B", acc_b), ("C", acc_c)):
            total_n[k] += n
            total_hit[k] += n * v

    logger.info("-" * 60)
    for k in ("A", "B", "C"):
        logger.info(f"{k}: {total_hit[k] / total_n[k]:.1%} ({total_n[k]} 场)")
        lines.append(f"{k}: {total_hit[k] / total_n[k]:.1%}")

    report = Path(__file__).resolve().parent.parent / "logs" / "backtest_odds_fusion.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"\n报告: {report}")


if __name__ == "__main__":
    main()
