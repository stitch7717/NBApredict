"""
分析回测中"模型押弱队"的案例：模型预测滚动胜率更低的一方赢球的场次。
输出: 案例表 + 命中率 + 模型做此判断依赖的特征（Ridge 系数 + 特征差异）。

用法:
    python scripts/upset_cases.py [--top 20]
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
from app.db.models import Team
from scripts.backtest_seasons import (
    TEST_SEASONS, MIN_PRIOR_GAMES, load_all_games, mode_b_features,
)

MIN_WP_GAP = 0.05  # 滚动胜率差 >= 5% 才算"押弱队"（排除势均力敌的场次）


def team_names() -> dict:
    with SessionLocal() as db:
        return {t.team_id: t.abbreviation for t in db.query(Team).all()}


def rolling_win_pcts(games: list) -> dict:
    """每场比赛时点滚动胜率: {(season, game_id): (home_wp, away_wp)}"""
    acc = defaultdict(lambda: {"wins": 0, "losses": 0})
    result = {}
    for g in games:
        hk = (g["home_team_id"], g["season"])
        ak = (g["away_team_id"], g["season"])
        h, a = acc[hk], acc[ak]
        if (h["wins"] + h["losses"]) >= MIN_PRIOR_GAMES and (a["wins"] + a["losses"]) >= MIN_PRIOR_GAMES:
            h_wp = h["wins"] / (h["wins"] + h["losses"])
            a_wp = a["wins"] / (a["wins"] + a["losses"])
            result[g["game_id"]] = (h_wp, a_wp)
        hs, as_ = g["home_score"], g["away_score"]
        for key, pf, pa in ((hk, hs, as_), (ak, as_, hs)):
            s = acc[key]
            if pf > pa:
                s["wins"] += 1
            else:
                s["losses"] += 1
    return result


def main(top: int = 20):
    games = load_all_games()
    names = team_names()
    wps = rolling_win_pcts(games)
    games_by_id = {g["game_id"]: g for g in games}

    X, y_home, y_away, seasons, playoffs, feature_names = mode_b_features(games)

    # 重建样本 -> game_id 对齐: mode_b_features 内部按相同顺序遍历，
    # 用 (season + 顺序) 无法直接对齐，改为自己重跑一遍拿到 game_id 列表
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
    assert len(sample_ids) == len(X), f"样本对齐失败 {len(sample_ids)} vs {len(X)}"

    seasons_arr = np.array(seasons)
    upset_rows = []
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

        idx = np.where(test_mask)[0]
        for k, i in enumerate(idx):
            gid = sample_ids[i]
            g = games_by_id[gid]
            h_wp, a_wp = wps[gid]
            pred_home_win = ph[k] > pa[k]
            if pred_home_win:
                pick_wp, opp_wp = h_wp, a_wp
                pick_team, opp_team = g["home_team_id"], g["away_team_id"]
                actual_home_win = g["home_score"] > g["away_score"]
                hit = actual_home_win
            else:
                pick_wp, opp_wp = a_wp, h_wp
                pick_team, opp_team = g["away_team_id"], g["home_team_id"]
                actual_home_win = g["home_score"] > g["away_score"]
                hit = not actual_home_win
            if opp_wp - pick_wp >= MIN_WP_GAP:
                upset_rows.append({
                    "season": test_season,
                    "date": str(g["game_date"]),
                    "pick": names.get(pick_team, "?"),
                    "opp": names.get(opp_team, "?"),
                    "pick_wp": pick_wp, "opp_wp": opp_wp,
                    "pick_home": pred_home_win,
                    "pred": (int(ph[k]), int(pa[k])),
                    "actual": (g["home_score"], g["away_score"]),
                    "hit": hit,
                    "features": X[i],
                })

    logger.info(f"模型押弱队的场次（胜率差 ≥ {MIN_WP_GAP:.0%}）: {len(upset_rows)} 场")
    hits = [r for r in upset_rows if r["hit"]]
    logger.info(f"其中押中: {len(hits)} 场, 命中率 {len(hits) / len(upset_rows):.1%}")

    # 案例表（命中 + 未命中的代表性案例）
    logger.info(f"\n{'赛季':<9}{'日期':<12}{'押的弱队':>6}{'vs':>2}{'对手':<6}{'弱队胜率':>8}{'对手胜率':>8}{'预测比分':>10}{'实际比分':>10}{'结果':>4}")
    shown = 0
    for r in upset_rows:
        if shown >= top:
            break
        pred = f"{r['pred'][0]}-{r['pred'][1]}" if r["pick_home"] else f"{r['pred'][1]}-{r['pred'][0]}"
        logger.info(
            f"{r['season']:<9}{r['date']:<12}{r['pick']:>6}{'vs':>2}{r['opp']:<6}"
            f"{r['pick_wp']:>8.1%}{r['opp_wp']:>8.1%}{pred:>10}"
            f"{r['actual'][0]}-{r['actual'][1] if r['pick_home'] else r['actual'][0]:<9}"
            f"{'✓' if r['hit'] else '✗':>4}"
        )
        shown += 1

    # 判断依据: 押弱队的场次里，哪些特征与平均场次差异最大（标准化后）
    all_feat = X
    upset_feat = np.array([r["features"] for r in upset_rows])
    mean_all = all_feat.mean(axis=0)
    mean_upset = upset_feat.mean(axis=0)
    diff = mean_upset - mean_all
    order = np.argsort(-np.abs(diff))[:8]
    logger.info("\n押弱队的场次中，与平均场次差异最大的特征（模型做判断的主要依据）:")
    for i in order:
        logger.info(f"  {feature_names[i]:<20} 平均偏离 {diff[i]:+.2f}σ")

    # 引用 Ridge 系数说明方向性（用最后一个测试赛季的模型）
    coef = m_home.coef_
    logger.info("\n相关特征的 Ridge 系数（最后一赛季模型，绝对值越大影响越大）:")
    for i in order:
        logger.info(f"  {feature_names[i]:<20} coef={coef[i]:+.3f}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    main(top=args.top)
