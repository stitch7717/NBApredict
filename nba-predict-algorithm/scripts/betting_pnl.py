"""
下注模拟：每场固定 10 元，按盘口 moneyline 赔率结算，统计每赛季盈亏。

两个策略对比:
  1. 跟模型: 按 mode B 走查回测的预测下注
  2. 跟盘口: 每场押盘口热门（市场基准，理论上亏损 ≈ 抽水 ~4-5%）

美国盘结算:
  正赔率 +X: 赢则净赚 10 * X/100
  负赔率 -X: 赢则净赚 10 * 100/X
  输则 -10

注意: moneyline 在 2023-24 只有 664 场、2024-25/2025-26 完全缺失（数据集本身），
这些赛季的盈亏只统计有赔率的比赛，并标注覆盖。

用法:
    python scripts/betting_pnl.py [--stake 10]
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
from app.db.models import GameRecord, OddsData
from scripts.backtest_seasons import MIN_PRIOR_GAMES, TEST_SEASONS, load_all_games, mode_b_features


def profit_of(odds: float, stake: float) -> float:
    """美国盘下单赢的净收益"""
    if odds > 0:
        return stake * odds / 100.0
    return stake * 100.0 / -odds


def main(stake: float = 10.0):
    with SessionLocal() as db:
        odds_rows = db.query(OddsData).all()
    by_game = {}
    for o in odds_rows:
        if o.home_win_odds is not None and o.away_win_odds is not None:
            by_game[o.game_id] = o

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

    model_pick = {}   # game_id -> 1 押主队 / 0 押客队
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
            model_pick[sample_ids[pos]] = 1 if ph[i] > pa[i] else 0

    logger.info(f"{'赛季':<10}{'策略':<8}{'下注场':>7}{'胜':>5}{'负':>5}{'命中率':>8}{'盈亏(元)':>10}{'ROI':>8}{'赔率覆盖':>9}")
    lines = []
    model_total = {"n": 0, "w": 0, "pnl": 0.0, "staked": 0.0}
    fav_total = {"n": 0, "w": 0, "pnl": 0.0, "staked": 0.0}
    for season in TEST_SEASONS:
        s_games = [g for g in games if g["season"] == season and g["game_id"] in by_game]
        cov = len(s_games)
        for strategy, total in (("模型", model_total), ("盘口", fav_total)):
            n = w = 0
            pnl = 0.0
            for g in s_games:
                o = by_game[g["game_id"]]
                home_win = g["home_score"] > g["away_score"]
                if strategy == "模型":
                    pick_home = model_pick.get(g["game_id"])
                    if pick_home is None:
                        continue
                else:
                    pick_home = o.home_win_prob >= o.away_win_prob
                odds = o.home_win_odds if pick_home else o.away_win_odds
                if odds is None:
                    continue
                n += 1
                if pick_home == home_win:
                    w += 1
                    pnl += profit_of(odds, stake)
                else:
                    pnl -= stake
            acc_rate = w / n if n else 0
            roi = pnl / (n * stake) if n else 0
            logger.info(
                f"{season:<10}{strategy:<8}{n:>7}{w:>5}{n - w:>5}{acc_rate:>8.1%}"
                f"{pnl:>+10.2f}{roi:>+8.1%}{cov:>9}"
            )
            lines.append(f"{season:<10}{strategy:<8}{n:>7}{w:>5}{n - w:>5}{acc_rate:>8.1%}{pnl:>+10.2f}{roi:>+8.1%}{cov:>9}")
            total["n"] += n
            total["w"] += w
            total["pnl"] += pnl
            total["staked"] += n * stake

    logger.info("-" * 75)
    for label, t in (("模型汇总", model_total), ("盘口汇总", fav_total)):
        acc_rate = t["w"] / t["n"] if t["n"] else 0
        roi = t["pnl"] / t["staked"] if t["staked"] else 0
        logger.info(
            f"{label:<10}{'':<8}{t['n']:>7}{t['w']:>5}{t['n'] - t['w']:>5}{acc_rate:>8.1%}"
            f"{t['pnl']:>+10.2f}{roi:>+8.1%}"
        )
        lines.append(f"{label}: n={t['n']}, pnl={t['pnl']:+.2f}, roi={roi:+.1%}")

    report = Path(__file__).resolve().parent.parent / "logs" / "betting_pnl.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"\n报告: {report}")
    logger.info("注意: 2022-23 只有 664 场有 moneyline（该赛季下半段起数据缺失）, "
                "2023-24/2024-25/2025-26 无 moneyline 数据（盈亏未计算）")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--stake", type=float, default=10.0)
    args = parser.parse_args()
    main(stake=args.stake)
