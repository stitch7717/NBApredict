"""
每赛季数据画像 + 去离群后的预测准确度（常规赛/季后赛分开算）。

第一步: 每赛季数据画像
  - 场次、分差均值/中位数/标准差、总分均值/标准差、主胜率
  - 离群场次计数: |分差|>=25、|分差|>=30、总分<=170 或 >=250

第二步: 不同清洗口径下的模型准确度（mode B 走查 + 赔率融合）:
  口径 F0: 全部比赛
  口径 F1: 去掉 |分差|>=25 的场次（大比分波动场）
  口径 F2: 去掉 |分差|>=20 的场次（更严格）
  口径 F3: 去掉总分 <=170 或 >=250 的极端得分场
  每个口径下常规赛 / 季后赛分别统计

用法:
    python scripts/analyze_season_quality.py
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

FILTERS = {
    "F0全部": None,
    "F1去分差25+": lambda d, t: abs(d) < 25,
    "F2去分差20+": lambda d, t: abs(d) < 20,
    "F3去极端总分": lambda d, t: 170 <= t <= 250,
}


def main():
    games = load_all_games()
    games_by_id = {g["game_id"]: g for g in games}

    with SessionLocal() as db:
        odds_rows = db.query(OddsData).all()
    diff_map = {o.game_id: -o.handicap_line for o in odds_rows if o.handicap_line is not None}

    # ---------- 第一步: 每赛季数据画像 ----------
    logger.info("=" * 78)
    logger.info("第一步: 每赛季数据画像（波动情况）")
    logger.info("=" * 78)
    logger.info(
        f"{'赛季':<10}{'常规赛':>6}{'季后赛':>6}{'分差均':>7}{'分差std':>8}{'总分均':>7}{'总分std':>8}"
        f"{'主胜率':>7}{'|diff|>=25':>10}{'|diff|>=30':>10}{'极端总分':>9}"
    )
    for season in ["2016-17"] + TEST_SEASONS:
        s_games = [g for g in games if g["season"] == season]
        if not s_games:
            continue
        diffs = [g["home_score"] - g["away_score"] for g in s_games]
        totals = [g["home_score"] + g["away_score"] for g in s_games]
        rs = [g for g in s_games if not g["is_playoff"]]
        po = [g for g in s_games if g["is_playoff"]]
        home_win = sum(1 for d in diffs if d > 0) / len(diffs)
        logger.info(
            f"{season:<10}{len(rs):>6}{len(po):>6}{np.mean(diffs):>+7.1f}{np.std(diffs):>8.1f}"
            f"{np.mean(totals):>7.1f}{np.std(totals):>8.1f}{home_win:>7.1%}"
            f"{sum(1 for d in diffs if abs(d) >= 25):>10}{sum(1 for d in diffs if abs(d) >= 30):>10}"
            f"{sum(1 for t in totals if t <= 170 or t >= 250):>9}"
        )

    # ---------- 第二步: 模型预测 + 各口径评估 ----------
    logger.info("\n" + "=" * 78)
    logger.info("第二步: 清洗口径 × 常规赛/季后赛 的模型准确度")
    logger.info("=" * 78)

    # 样本对齐
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

    # 每场: (season, is_playoff, diff, total, pred_diff, market_diff)
    records = {}
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
        for i, pos in enumerate(np.where(test_mask)[0]):
            gid = sample_ids[pos]
            g = games_by_id[gid]
            records[gid] = {
                "season": test_season,
                "playoff": g["is_playoff"],
                "diff": g["home_score"] - g["away_score"],
                "total": g["home_score"] + g["away_score"],
                "pred_diff": ph[i] - pa[i],
                "market_diff": diff_map.get(gid, 0.0),
            }

    header = f"{'口径':<12}{'常规赛':>9}{'季后赛':>9}{'全部':>9}{'常规赛B+赔率':>13}{'季后赛B+赔率':>13}"
    logger.info(header)
    lines = [header]
    for fname, fn in FILTERS.items():
        def keep(r):
            if fn is None:
                return True
            return fn(r["diff"], r["total"])

        rs_hit = rs_n = po_hit = po_n = 0
        rsb_hit = rsb_n = pob_hit = pob_n = 0
        for r in records.values():
            if not keep(r):
                continue
            pred_ok = (r["pred_diff"] > 0) == (r["diff"] > 0)
            fused = 0.3 * r["market_diff"] + 0.7 * r["pred_diff"]
            fused_ok = (fused > 0) == (r["diff"] > 0)
            if not r["playoff"]:
                rs_n += 1
                rs_hit += pred_ok
                rsb_n += 1
                rsb_hit += fused_ok
            else:
                po_n += 1
                po_hit += pred_ok
                pob_n += 1
                pob_hit += fused_ok
        rs_acc = rs_hit / max(rs_n, 1)
        po_acc = po_hit / max(po_n, 1)
        all_acc = (rs_hit + po_hit) / max(rs_n + po_n, 1)
        rsb_acc = rsb_hit / max(rsb_n, 1)
        pob_acc = pob_hit / max(pob_n, 1)
        row = f"{fname:<12}{rs_acc:>8.1%}{po_acc:>8.1%}{all_acc:>8.1%}{rsb_acc:>12.1%}{pob_acc:>12.1%}"
        logger.info(row)
        lines.append(row)

    report = Path(__file__).resolve().parent.parent / "logs" / "season_quality.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"\n报告: {report}")
    logger.info("说明: B+赔率 = 模型分差与市场分差按 7:3 融合（固定权重示例）")


if __name__ == "__main__":
    main()
