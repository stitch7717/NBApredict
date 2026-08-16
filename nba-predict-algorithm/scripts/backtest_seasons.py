"""
逐赛季预测准确性回测（2017-18 .. 2025-26）

两种模式:
  A. 线上口径（--mode A）: 复用 train_model.py 的特征（全赛季均值 + 赛季末近10场）。
     与生产模型一致，但含"未来信息泄漏"，准确性偏乐观。
  B. 诚实回测（--mode B，默认）: 时点特征——每场比赛只用其之前比赛的数据
     （滚动 ppg/oppg/胜率/主客场/近10场/节奏/效率），无泄漏，反映真实上线表现。

训练策略: 逐赛季走查（walk-forward）——预测赛季 S 时，用 S 之前所有赛季的比赛训练。

指标（每赛季 + 汇总）:
  - 场次数、胜率命中率、MAE(总分)、MAE(分差)
  - 基线对比: "永远猜主队"的命中率

用法:
    python scripts/backtest_seasons.py [--mode A|B] [--alpha 1.0]
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
from app.db.models import GameRecord, TeamData

# 测试赛季（2016-17 无前置训练数据，不参与走查）
TEST_SEASONS = [
    "2017-18", "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2025-26",
]

# 模式 B 特征名（全部可从比分推导，时点安全）
FEATURE_NAMES_B = [
    "home_ppg", "away_ppg", "home_oppg", "away_oppg",
    "home_win_pct", "away_win_pct",
    "home_recent_wr", "away_recent_wr",
    "home_off_rtg", "away_off_rtg", "home_def_rtg", "away_def_rtg",
    "home_pace", "away_pace", "pace_diff",
    "home_away_diff", "is_playoff",
    "home_momentum", "away_momentum",
]

MIN_PRIOR_GAMES = 5  # 时点特征冷启动门槛


def load_all_games() -> list:
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED",
        ).order_by(GameRecord.game_date).all()
        return [{
            "game_id": g.game_id,
            "season": g.season,
            "game_date": g.game_date,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_playoff": g.is_playoff,
        } for g in games]


# ---------- 模式 A: 线上口径特征（复用 train_model.py 逻辑） ----------

def mode_a_features(games: list):
    """复用生产模型特征（赛季均值 + 赛季末近10场，含泄漏）"""
    from scripts.train_model import (
        load_team_stats_from_db, compute_recent_stats, build_features, FEATURE_NAMES,
    )
    team_stats = load_team_stats_from_db()
    recent_stats = compute_recent_stats(games)
    all_seasons = sorted({g["season"] for g in games})
    X, y_h, y_a, seasons, playoffs = build_features(games, team_stats, recent_stats, all_seasons)
    return X, y_h, y_a, seasons, playoffs, FEATURE_NAMES


# ---------- 模式 B: 时点特征（无泄漏） ----------

def mode_b_features(games: list):
    """
    为每场比赛构建只使用其之前比赛数据的特征。
    返回: (X, y_home, y_away, seasons, names)
    """
    # 滚动累积器: (team_id, season) -> dict
    acc = defaultdict(lambda: {
        "wins": 0, "losses": 0,
        "pf": [], "pa": [],
        "home_pf": [], "home_pa": [],
        "away_pf": [], "away_pa": [],
        "results": [],  # [(date, pf, pa)] 按时间排序，用于近10场
    })

    league_total = 210.0  # 联赛场均总分初始估计

    X, y_home, y_away, seasons_out, playoffs_out = [], [], [], [], []

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
            X.append(features)
            y_home.append(g["home_score"])
            y_away.append(g["away_score"])
            seasons_out.append(g["season"])
            playoffs_out.append(g["is_playoff"])

        # 更新滚动状态（本场结果只在后续比赛可见）
        hs, as_ = g["home_score"], g["away_score"]
        for key, pf, pa, is_home in (
            (hk, hs, as_, True), (ak, as_, hs, False),
        ):
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

    return (np.array(X), np.array(y_home), np.array(y_away), seasons_out,
            np.array(playoffs_out), FEATURE_NAMES_B)


# ---------- 回测主流程 ----------

def evaluate(y_home, y_away, pred_h, pred_a):
    """计算一个测试集的指标（总体 + 常规赛/季后赛拆分）"""
    n = len(y_home)
    if n == 0:
        return None
    mae_total = float(np.mean(np.abs(pred_h + pred_a - y_home - y_away)))
    mae_diff = float(np.mean(np.abs((pred_h - pred_a) - (y_home - y_away))))
    correct = np.sum((pred_h > pred_a) == (y_home > y_away))
    win_acc = float(correct / n)
    home_baseline = float(np.mean(y_home > y_away))
    return {"n": n, "mae_total": mae_total, "mae_diff": mae_diff,
            "win_acc": win_acc, "home_baseline": home_baseline}


def evaluate_split(y_home, y_away, pred_h, pred_a, playoffs):
    """按常规赛/季后赛拆分评估，返回 {overall, regular, playoff}"""
    result = {"overall": evaluate(y_home, y_away, pred_h, pred_a)}
    for label, mask in (("regular", playoffs == 0), ("playoff", playoffs == 1)):
        result[label] = evaluate(y_home[mask], y_away[mask], pred_h[mask], pred_a[mask])
    return result


def run(mode: str = "B", alpha: float = 1.0):
    logger.info(f"模式 {'A(线上口径, 含泄漏)' if mode == 'A' else 'B(诚实回测, 无泄漏)'}, alpha={alpha}")

    games = load_all_games()
    logger.info(f"加载 {len(games)} 场比赛")

    if mode == "A":
        X, y_home, y_away, seasons, playoffs, names = mode_a_features(games)
    else:
        X, y_home, y_away, seasons, playoffs, names = mode_b_features(games)
    logger.info(f"特征样本 {len(X)} 场, 特征数 {len(names)}")

    seasons_arr = np.array(seasons)
    playoffs = np.array(playoffs)
    results = []
    rows_all = []

    for test_season in TEST_SEASONS:
        train_mask = np.array([s < test_season for s in seasons])
        test_mask = seasons_arr == test_season
        if train_mask.sum() < 100 or test_mask.sum() == 0:
            logger.warning(f"{test_season}: 训练 {train_mask.sum()} 场 / 测试 {test_mask.sum()} 场，跳过")
            continue

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[train_mask])
        X_te = scaler.transform(X[test_mask])

        m_home = Ridge(alpha=alpha).fit(X_tr, y_home[train_mask])
        m_away = Ridge(alpha=alpha).fit(X_tr, y_away[train_mask])

        pred_h = np.round(m_home.predict(X_te)).astype(int)
        pred_a = np.round(m_away.predict(X_te)).astype(int)

        r = evaluate_split(y_home[test_mask], y_away[test_mask], pred_h, pred_a, playoffs[test_mask])
        results.append((test_season, r))
        rows_all.append({
            "season": test_season,
            "y_home": y_home[test_mask], "y_away": y_away[test_mask],
            "pred_h": pred_h, "pred_a": pred_a,
            "playoffs": playoffs[test_mask],
        })
        o, reg, po = r["overall"], r["regular"], r["playoff"]
        logger.info(
            f"{test_season}: 总 {o['n']:>4} 场胜率 {o['win_acc']:.1%} | "
            f"常规赛 {reg['n']:>4} 场胜率 {reg['win_acc']:.1%} | "
            f"季后赛 {po['n']:>3} 场胜率 {po['win_acc']:.1%} | "
            f"MAE总分 {o['mae_total']:.2f}"
        )

    if not results:
        logger.error("无有效回测结果")
        return

    # 汇总
    yh = np.concatenate([r["y_home"] for r in rows_all])
    ya = np.concatenate([r["y_away"] for r in rows_all])
    ph = np.concatenate([r["pred_h"] for r in rows_all])
    pa = np.concatenate([r["pred_a"] for r in rows_all])
    pof = np.concatenate([r["playoffs"] for r in rows_all])
    overall = evaluate_split(yh, ya, ph, pa, pof)

    logger.info("\n" + "=" * 60)
    logger.info(f"汇总 ({mode} 模式, {len(results)} 个测试赛季):")
    for label, title in (("overall", "全部"), ("regular", "常规赛"), ("playoff", "季后赛")):
        m = overall[label]
        if m is None:
            continue
        logger.info(
            f"  {title}: {m['n']} 场, 胜率命中率 {m['win_acc']:.1%} "
            f"(基线猜主队 {m['home_baseline']:.1%}, 超出 {m['win_acc'] - m['home_baseline']:+.1%}), "
            f"MAE总分 {m['mae_total']:.2f}, MAE分差 {m['mae_diff']:.2f}"
        )
    logger.info("=" * 60)

    # 报告落盘
    report = Path(__file__).resolve().parent.parent / "logs" / f"backtest_{mode}_{test_season}.txt"
    lines = [f"backtest mode={mode}, alpha={alpha}", ""]
    lines.append(
        f"{'season':<10}{'类型':<6}{'n':>5}{'win_acc':>10}{'home_bl':>10}{'mae_total':>11}{'mae_diff':>10}"
    )
    for season, r in results:
        for label, title in (("overall", "总"), ("regular", "常规"), ("playoff", "季后")):
            m = r[label]
            if m:
                lines.append(
                    f"{season:<10}{title:<6}{m['n']:>5}{m['win_acc']:>10.1%}{m['home_baseline']:>10.1%}"
                    f"{m['mae_total']:>11.2f}{m['mae_diff']:>10.2f}"
                )
    for label, title in (("overall", "汇总总"), ("regular", "汇总常规"), ("playoff", "汇总季后")):
        m = overall[label]
        if m:
            lines.append(
                f"{title:<10}{'':<6}{m['n']:>5}{m['win_acc']:>10.1%}{m['home_baseline']:>10.1%}"
                f"{m['mae_total']:>11.2f}{m['mae_diff']:>10.2f}"
            )
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"报告已保存: {report}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["A", "B"], default="B")
    parser.add_argument("--alpha", type=float, default=1.0)
    args = parser.parse_args()
    run(mode=args.mode, alpha=args.alpha)
