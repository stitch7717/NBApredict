"""
盘口基线回测：'永远押盘口热门（赔率隐含概率更高者）'的每赛季命中率，
并与模型回测（mode B, 65.1%）在同口径比赛集上对比。

同时统计: 让分盘热门的赢盘率（ATS, 覆盖让分线的比例）。

用法:
    python scripts/backtest_odds_baseline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, OddsData
from scripts.backtest_seasons import TEST_SEASONS, load_all_games, mode_b_features
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def main():
    with SessionLocal() as db:
        odds = db.query(OddsData).all()
    by_game = {}
    for o in odds:
        by_game.setdefault(o.game_id, o)

    games = load_all_games()
    games_with_odds = [g for g in games if g["game_id"] in by_game]
    logger.info(f"有赔率的比赛: {len(games_with_odds)} / {len(games)}")

    logger.info(f"\n{'赛季':<10}{'盘口热门':>12}{'模型(同集)':>14}{'猜主队':>12}{'让分赢盘':>12}{'场次':>7}")
    rows = []
    for season in TEST_SEASONS:
        s_games = [g for g in games_with_odds if g["season"] == season]
        if not s_games:
            continue
        fav_hit = 0
        fav_n = 0
        home_hit = 0
        ats_hit = 0
        ats_n = 0
        for g in s_games:
            o = by_game[g["game_id"]]
            home_win = g["home_score"] > g["away_score"]
            # 盘口热门: moneyline 隐含概率更高者；moneyline 缺失时用让分盘（让分方为热门）
            fav_home = None
            if o.home_win_prob and o.away_win_prob and o.home_win_prob != o.away_win_prob:
                fav_home = o.home_win_prob >= o.away_win_prob
            elif o.handicap_line is not None:
                fav_home = o.handicap_line < 0  # 主队让分 = 主队是热门
            if fav_home is not None:
                fav_n += 1
                if fav_home == home_win:
                    fav_hit += 1
            if home_win:
                home_hit += 1
            # 让分赢盘: 主队赢盘 = (主队分 - 让分) > 客队分（handicap_line 为主队让分，负值）
            if o.handicap_line is not None:
                ats_n += 1
                home_cover = (g["home_score"] - g["away_score"]) > -o.handicap_line
                # 让分盘口方 = 让分更小的一方（负更多是热门）
                if home_cover and o.handicap_line <= 0:
                    ats_hit += 1
                elif not home_cover and o.handicap_line > 0:
                    ats_hit += 1
        n = len(s_games)
        fav_acc = fav_hit / max(fav_n, 1)
        home_acc = home_hit / n
        ats_acc = ats_hit / max(ats_n, 1)
        logger.info(f"{season:<10}{fav_acc:>11.1%}{'—':>14}{home_acc:>11.1%}{ats_acc:>11.1%}{n:>7}")
        rows.append((season, n, fav_n, fav_acc, home_acc, ats_acc, ats_n))

    # 模型在同集上的命中率（精确对齐有赔率比赛的 game_id）
    logger.info("\n计算模型在有赔率比赛集上的命中率（精确同集）...")
    from collections import defaultdict
    from scripts.backtest_seasons import MIN_PRIOR_GAMES
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
    assert len(sample_ids) == len(X), f"对齐失败 {len(sample_ids)} vs {len(X)}"
    seasons_arr = np.array(seasons)
    odds_ids = set(by_game.keys())
    has_odds = np.array([gid in odds_ids for gid in sample_ids])

    model_by_season = {}
    model_total_hit = model_total_n = 0
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
        same = has_odds[test_pos]
        if same.sum() == 0:
            continue
        hit = np.sum((ph[same] > pa[same]) == (y_home[test_pos][same] > y_away[test_pos][same]))
        model_by_season[test_season] = float(hit / same.sum())
        model_total_hit += hit
        model_total_n += same.sum()
    model_total = model_total_hit / max(model_total_n, 1)

    # 汇总
    total_n = sum(r[1] for r in rows)
    total_fav_n = sum(r[2] for r in rows)
    total_fav = sum(r[3] * r[2] for r in rows) / max(total_fav_n, 1)
    total_home = sum(r[4] * r[1] for r in rows) / total_n
    total_ats = sum(r[5] * r[6] for r in rows) / max(sum(r[6] for r in rows), 1)
    logger.info("-" * 70)
    logger.info(f"{'汇总':<10}{total_fav:>11.1%}{model_total:>13.1%}{total_home:>11.1%}{total_ats:>11.1%}{total_n:>7}")
    logger.info(f"\n模型 mode B 各赛季（有赔率比赛同集口径）:")
    for s in TEST_SEASONS:
        if s in model_by_season:
            logger.info(f"  {s}: {model_by_season[s]:.1%}")
    logger.info("\n结论: 盘口热门命中率是市场基准（预期 67-70%）。模型跑赢它才算有超额收益。")


if __name__ == "__main__":
    main()
