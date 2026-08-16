"""
大小分（总分盘）回测：模型预测总分 vs 盘口大小分线。

指标（每赛季 + 汇总，全部 10 个赛季——total 线数据完整）:
  - 大/小命中率: 预测总分 > 盘口线 → 买大, 否则买小; 与实际总分方向一致为命中
  - 预测总分误差: MAE 与平均偏差（模型总分是否系统性高/低估）
  - 平赔下注模拟: 按 1.91/1.91 固定赔率（标准 5% 抽水），每注 10 元买大/小盈亏

用法:
    python scripts/backtest_totals.py [--stake 10]
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

FLAT_ODDS = 1.91  # 大小分标准平赔


def main(stake: float = 10.0):
    with SessionLocal() as db:
        odds_rows = db.query(OddsData).all()
    line_by_game = {}
    for o in odds_rows:
        if o.total_line is not None:
            line_by_game[o.game_id] = o.total_line

    games = load_all_games()
    games_by_id = {g["game_id"]: g for g in games}

    # 模型走查预测（与 game_id 对齐）
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
    seasons_arr = np.array(seasons)

    pred_total = {}   # game_id -> 预测总分
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
        test_pos = np.where(test_mask)[0]
        for i, pos in enumerate(test_pos):
            pred_total[sample_ids[pos]] = ph[i] + pa[i]

    logger.info(f"{'赛季':<10}{'场次':>6}{'大/小命中':>10}{'总分MAE':>9}{'总分偏差':>9}{'盈亏(元)':>10}{'ROI':>8}")
    lines = []
    total = {"n": 0, "hit": 0, "mae_sum": 0.0, "bias_sum": 0.0, "pnl": 0.0, "staked": 0.0}
    for season in TEST_SEASONS:
        s_games = [g for g in games if g["season"] == season]
        n = hit = 0
        mae_sum = bias_sum = 0.0
        pnl = 0.0
        for g in s_games:
            pt = pred_total.get(g["game_id"])
            line = line_by_game.get(g["game_id"])
            if pt is None or line is None:
                continue
            actual = g["home_score"] + g["away_score"]
            n += 1
            mae_sum += abs(pt - actual)
            bias_sum += pt - actual
            # 大小方向
            pred_over = pt > line
            actual_over = actual > line
            if pred_over == actual_over:
                hit += 1
                pnl += stake * (FLAT_ODDS - 1)
            else:
                pnl -= stake
        acc_rate = hit / n if n else 0
        mae = mae_sum / n if n else 0
        bias = bias_sum / n if n else 0
        roi = pnl / (n * stake) if n else 0
        logger.info(f"{season:<10}{n:>6}{acc_rate:>9.1%}{mae:>9.2f}{bias:>+9.2f}{pnl:>+10.2f}{roi:>+8.1%}")
        lines.append(f"{season:<10}{n:>6}{acc_rate:>9.1%}{mae:>9.2f}{bias:>+9.2f}{pnl:>+10.2f}{roi:>+8.1%}")
        total["n"] += n
        total["hit"] += hit
        total["mae_sum"] += mae_sum
        total["bias_sum"] += bias_sum
        total["pnl"] += pnl
        total["staked"] += n * stake

    n = total["n"]
    logger.info("-" * 65)
    logger.info(
        f"{'汇总':<10}{n:>6}{total['hit'] / n:>9.1%}{total['mae_sum'] / n:>9.2f}"
        f"{total['bias_sum'] / n:>+9.2f}{total['pnl']:>+10.2f}{total['pnl'] / total['staked']:>+8.1%}"
    )
    lines.append(
        f"汇总: n={n}, hit={total['hit'] / n:.1%}, mae={total['mae_sum'] / n:.2f}, "
        f"bias={total['bias_sum'] / n:+.2f}, pnl={total['pnl']:+.2f}"
    )

    report = Path(__file__).resolve().parent.parent / "logs" / "backtest_totals.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"\n报告: {report}")
    logger.info("说明: 盈亏按 1.91 平赔固定赔率（5% 抽水）模拟；偏差为 预测总分-实际总分")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--stake", type=float, default=10.0)
    args = parser.parse_args()
    main(stake=args.stake)
