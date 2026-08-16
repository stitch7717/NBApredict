"""
伤病感知回测对比：同一批测试赛季上，无伤病特征 vs 有伤病特征的模型表现。

伤病特征（时点安全）: 每场比赛当天，双方"因伤缺阵球员"的赛季场均得分合计
  home_missing_ppg / away_missing_ppg
  - 缺阵窗口: injury_date <= 比赛日 <= return_date（无复出日期则视为赛季余下时间缺阵）
  - 球员归属球队: player_roster 该赛季记录

注意: 历史伤病数据（tylerferguson 数据集）只覆盖 2016-17..2019-20 四个赛季，
因此本对比的测试赛季为 2017-18 / 2018-19 / 2019-20。

用法:
    python scripts/backtest_injuries.py
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
from app.db.models import InjuryRecord, PlayerData, PlayerRoster
from scripts.backtest_seasons import (
    FEATURE_NAMES_B, MIN_PRIOR_GAMES, TEST_SEASONS, load_all_games,
)

INJURY_TEST_SEASONS = ["2017-18", "2018-19", "2019-20"]
INJURY_FEATURE_NAMES = FEATURE_NAMES_B + ["home_missing_ppg", "away_missing_ppg"]


def load_injury_windows() -> dict:
    """{player_id: [(injury_date, return_date_or_None, season), ...]}"""
    with SessionLocal() as db:
        rows = db.query(InjuryRecord).all()
    result = defaultdict(list)
    for r in rows:
        result[r.player_id].append((r.injury_date, r.return_date, r.season))
    return result


def load_player_ppg() -> dict:
    """{(player_id, season): 场均得分}"""
    with SessionLocal() as db:
        rows = db.query(PlayerData).all()
    return {(r.player_id, r.season): (r.points_per_game or 0) for r in rows}


def load_roster_teams() -> dict:
    """{(team_id, season): [player_id, ...]}"""
    with SessionLocal() as db:
        rows = db.query(PlayerRoster).all()
    result = defaultdict(list)
    for r in rows:
        result[(r.team_id, r.season)].append(r.player_id)
    return result


def is_out(windows, player_id: int, game_date) -> bool:
    for start, end, _ in windows.get(player_id, []):
        if start is None:
            continue
        if start <= game_date and (end is None or game_date <= end):
            return True
    return False


def build_samples(games: list, with_injuries: bool):
    """滚动时点特征（复用 mode B 逻辑）+ 可选伤病特征，返回 (X, y, seasons, playoffs, game_ids)"""
    windows = load_injury_windows() if with_injuries else None
    ppg = load_player_ppg() if with_injuries else None
    roster = load_roster_teams() if with_injuries else None

    acc = defaultdict(lambda: {
        "wins": 0, "losses": 0,
        "pf": [], "pa": [],
        "home_pf": [], "home_pa": [],
        "away_pf": [], "away_pa": [],
        "results": [],
    })
    league_total = 210.0

    X, y_home, y_away, seasons_out, playoffs_out, game_ids = [], [], [], [], [], []

    for g in games:
        hk = (g["home_team_id"], g["season"])
        ak = (g["away_team_id"], g["season"])
        h, a = acc[hk], acc[ak]

        if len(h["pf"]) >= MIN_PRIOR_GAMES and len(a["pf"]) >= MIN_PRIOR_GAMES:
            h_ppg = sum(h["pf"]) / len(h["pf"])
            h_oppg = sum(h["pa"]) / len(h["pa"])
            a_ppg = sum(a["pf"]) / len(a["pf"])
            a_oppg = sum(a["pa"]) / len(a["pa"])
            h_win_pct = h["wins"] / max(h["wins"] + h["losses"], 1)
            a_win_pct = a["wins"] / max(a["wins"] + a["losses"], 1)

            h_recent = h["results"][-10:]
            a_recent = a["results"][-10:]
            h_recent_wr = sum(1 for _, pf, pa in h_recent if pf > pa) / len(h_recent)
            a_recent_wr = sum(1 for _, pf, pa in a_recent if pf > pa) / len(a_recent)
            h_mom = sum(pf for _, pf, _ in h_recent) / len(h_recent)
            a_mom = sum(pf for _, pf, _ in a_recent) / len(a_recent)

            h_home_ppg = sum(h["home_pf"]) / len(h["home_pf"]) if h["home_pf"] else h_ppg
            a_away_ppg = sum(a["away_pf"]) / len(a["away_pf"]) if a["away_pf"] else a_ppg
            h_pace = (h_ppg + h_oppg) / league_total * 100
            a_pace = (a_ppg + a_oppg) / league_total * 100
            h_ortg = h_ppg / max(h_pace, 1) * 100
            h_drtg = h_oppg / max(h_pace, 1) * 100
            a_ortg = a_ppg / max(a_pace, 1) * 100
            a_drtg = a_oppg / max(a_pace, 1) * 100

            features = [
                h_ppg, a_ppg, h_oppg, a_oppg,
                h_win_pct, a_win_pct,
                h_recent_wr, a_recent_wr,
                h_ortg, a_ortg, h_drtg, a_drtg,
                h_pace, a_pace, h_pace - a_pace,
                h_home_ppg - a_away_ppg,
                g["is_playoff"],
                h_mom, a_mom,
            ]

            if with_injuries:
                h_missing = sum(
                    ppg.get((pid, g["season"]), 0)
                    for pid in roster.get((g["home_team_id"], g["season"]), [])
                    if is_out(windows, pid, g["game_date"])
                )
                a_missing = sum(
                    ppg.get((pid, g["season"]), 0)
                    for pid in roster.get((g["away_team_id"], g["season"]), [])
                    if is_out(windows, pid, g["game_date"])
                )
                features += [h_missing, a_missing]

            X.append(features)
            y_home.append(g["home_score"])
            y_away.append(g["away_score"])
            seasons_out.append(g["season"])
            playoffs_out.append(g["is_playoff"])
            game_ids.append(g["game_id"])

        hs, as_ = g["home_score"], g["away_score"]
        for key, pf, pa, is_home in ((hk, hs, as_, True), (ak, as_, hs, False)):
            s = acc[key]
            s["pf"].append(pf)
            s["pa"].append(pa)
            s["results"].append((g["game_date"], pf, pa))
            if is_home:
                s["home_pf"].append(pf)
                s["home_pa"].append(pa)
            else:
                s["away_pf"].append(pf)
                s["away_pa"].append(pa)
            if pf > pa:
                s["wins"] += 1
            else:
                s["losses"] += 1

    return (np.array(X), np.array(y_home), np.array(y_away),
            seasons_out, np.array(playoffs_out), game_ids)


def run_backtest(X, y_home, y_away, seasons, test_seasons, alpha=1.0):
    """走查回测，返回 [(season, n, win_acc, mae_total)]"""
    seasons_arr = np.array(seasons)
    results = []
    for test_season in test_seasons:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            continue
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])
        m_home = Ridge(alpha=alpha).fit(X_tr, y_home[train_mask])
        m_away = Ridge(alpha=alpha).fit(X_tr, y_away[train_mask])
        ph = np.round(m_home.predict(X_te)).astype(int)
        pa = np.round(m_away.predict(X_te)).astype(int)
        n = len(ph)
        win_acc = float(np.mean((ph > pa) == (y_home[test_mask] > y_away[test_mask])))
        mae_total = float(np.mean(np.abs(ph + pa - y_home[test_mask] - y_away[test_mask])))
        results.append((test_season, n, win_acc, mae_total))
    return results


def main():
    games = load_all_games()
    logger.info(f"共 {len(games)} 场比赛")

    logger.info("构建无伤病特征样本...")
    X0, y0h, y0a, s0, _, _ = build_samples(games, with_injuries=False)
    logger.info("构建有伤病特征样本...")
    X1, y1h, y1a, s1, _, _ = build_samples(games, with_injuries=True)
    logger.info(f"无伤病: {len(X0)} 样本, 有伤病: {len(X1)} 样本（特征数 {X1.shape[1]}）")

    r0 = run_backtest(X0, y0h, y0a, s0, INJURY_TEST_SEASONS)
    r1 = run_backtest(X1, y1h, y1a, s1, INJURY_TEST_SEASONS)

    logger.info(f"\n{'赛季':<10}{'无伤病胜率':>14}{'有伤病胜率':>14}{'提升':>10}{'无伤病MAE':>12}{'有伤病MAE':>12}")
    for (season, n, acc0, mae0), (_, _, acc1, mae1) in zip(r0, r1):
        logger.info(f"{season:<10}{acc0:>13.1%}{acc1:>13.1%}{acc1 - acc0:>+9.1%}{mae0:>12.2f}{mae1:>12.2f}")
    total0 = np.mean([r[2] for r in r0])
    total1 = np.mean([r[2] for r in r1])
    logger.info("-" * 60)
    logger.info(f"{'平均':<10}{total0:>13.1%}{total1:>13.1%}{total1 - total0:>+9.1%}")

    # 伤病特征的系数（最后赛季模型）
    scaler = StandardScaler()
    seasons_arr = np.array(s1)
    test_season = INJURY_TEST_SEASONS[-1]
    train_mask = np.array([s < test_season for s in s1])
    X_tr = scaler.fit_transform(X1[train_mask])
    m_home = Ridge(alpha=1.0).fit(X_tr, y1h[train_mask])
    coefs = {name: round(float(c), 3) for name, c in zip(INJURY_FEATURE_NAMES, m_home.coef_)}
    logger.info(f"\n伤病特征系数（{test_season} 模型）:")
    logger.info(f"  home_missing_ppg: {coefs['home_missing_ppg']}")
    logger.info(f"  away_missing_ppg: {coefs['away_missing_ppg']}")


if __name__ == "__main__":
    main()
