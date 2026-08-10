"""
系数优化脚本
用网格搜索优化预测系数，最小化 MAE
"""
import sys
import json
from pathlib import Path
from itertools import product

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, TeamData, AlgorithmParamSnapshot

# 使用最完整的赛季进行优化
TUNE_SEASONS = [
    ("2022-23", "2023-24"),
    ("2023-24", "2024-25"),
]

# 可调系数网格
PARAM_GRID = {
    # 实力系数权重 (win, off, def) - 需要总和=1.0
    "strength_weights": [
        (0.4, 0.3, 0.3),  # 当前默认
        (0.35, 0.35, 0.30),
        (0.30, 0.40, 0.30),
        (0.45, 0.25, 0.30),
        (0.30, 0.30, 0.40),
    ],
    # 主场优势基数
    "home_base": [1.03, 1.04, 1.055, 1.07, 1.08],
    # 季后赛加成
    "playoff_boost": [1.0, 1.03, 1.05, 1.08],
    # 进攻效率基准 (off_rtg / base)
    "off_rtg_base": [108.0, 110.0, 112.0, 114.0],
    # 防守效率基准
    "def_rtg_base": [108.0, 110.0, 112.0, 114.0],
    # 风格克制系数范围
    "style_strong": [1.02, 1.03, 1.05],
    "style_weak": [0.95, 0.97, 0.98],
}


def _get(td, key, default=0):
    if isinstance(td, dict):
        return td.get(key) or default
    return getattr(td, key, None) or default


def load_team_data_map(season: str) -> dict:
    with SessionLocal() as db:
        rows = db.query(TeamData).filter(TeamData.season == season).all()
        result = {}
        for r in rows:
            result[r.team_id] = {
                "win_percentage": r.win_percentage,
                "offensive_rating": r.offensive_rating,
                "defensive_rating": r.defensive_rating,
                "home_wins": r.home_wins,
                "home_losses": r.home_losses,
                "points_per_game": r.points_per_game,
                "three_percentage": r.three_percentage,
                "opponent_three_pct": r.opponent_three_pct,
            }
        return result


def load_games(season: str) -> list:
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.season == season,
            GameRecord.status == "FINISHED",
        ).all()
        return [{
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_playoff": g.is_playoff,
        } for g in games]


def predict_with_params(home_td, away_td, is_playoff, params) -> tuple:
    """使用指定参数预测比赛"""
    sw = params["strength_weights"]

    # 实力系数
    def calc_sc(td):
        wp = _get(td, "win_percentage", 0.5)
        off = _get(td, "offensive_rating", 110.0)
        deff = _get(td, "defensive_rating", 110.0)
        wf = 0.8 + (wp * 0.4)
        of = off / params["off_rtg_base"]
        df = params["def_rtg_base"] / max(deff, 90.0)
        return wf * sw[0] + of * sw[1] + df * sw[2]

    home_sc = calc_sc(home_td)
    away_sc = calc_sc(away_td)

    # 主场优势
    hw = _get(home_td, "home_wins", 0)
    hl = _get(home_td, "home_losses", 0)
    home_c = params["home_base"]
    if hw and hl and (hw + hl) > 0:
        home_c = 1.03 + ((hw / (hw + hl)) * 0.05)

    # 场景系数
    scene_c = params["playoff_boost"] if is_playoff else 1.0

    # 风格克制
    h_off = _get(home_td, "offensive_rating", 110.0)
    h_def = _get(home_td, "defensive_rating", 110.0)
    a_off = _get(away_td, "offensive_rating", 110.0)
    a_def = _get(away_td, "defensive_rating", 110.0)

    h_type = "进攻型" if h_off > h_def else "防守型"
    a_type = "进攻型" if a_off > a_def else "防守型"

    style_c = 1.0
    if h_type == "进攻型" and a_type == "防守型":
        tp = _get(away_td, "opponent_three_pct", 0.35)
        style_c = params["style_weak"] if tp < 0.34 else params["style_strong"]
    elif h_type == "防守型" and a_type == "进攻型":
        tp = _get(home_td, "three_percentage", 0.35)
        style_c = params["style_strong"] if tp > 0.38 else params["style_weak"]

    home_total = home_sc * home_c * scene_c * style_c
    away_total = away_sc * scene_c

    base_home = _get(home_td, "points_per_game", 110.0)
    base_away = _get(away_td, "points_per_game", 108.0)

    return round(base_home * home_total), round(base_away * away_total)


def evaluate_params(all_team_data: dict, all_games: list, params: dict) -> dict:
    """评估一组参数的预测效果"""
    predictions = []

    for game in all_games:
        home_td = all_team_data.get(game["home_team_id"])
        away_td = all_team_data.get(game["away_team_id"])
        if not home_td or not away_td:
            continue

        ph, pa = predict_with_params(home_td, away_td, game["is_playoff"], params)
        predictions.append({
            "ph": ph, "pa": pa,
            "ah": game["home_score"], "aa": game["away_score"],
        })

    if not predictions:
        return {"mae_total": 999, "mae_diff": 999, "win_acc": 0, "count": 0}

    n = len(predictions)
    mae_total = sum(abs(p["ph"] + p["pa"] - p["ah"] - p["aa"]) for p in predictions) / n
    mae_diff = sum(abs((p["ph"] - p["pa"]) - (p["ah"] - p["aa"])) for p in predictions) / n
    correct = sum(1 for p in predictions if (p["ph"] > p["pa"]) == (p["ah"] > p["aa"]))

    return {
        "mae_total": round(mae_total, 3),
        "mae_diff": round(mae_diff, 3),
        "win_acc": round(correct / n, 4),
        "count": n,
        "combined": round(mae_total + mae_diff * 1.5, 3),  # 加权综合指标
    }


def grid_search(all_team_data: dict, all_games: list) -> tuple:
    """网格搜索最优参数"""
    # 生成所有参数组合
    keys = ["strength_weights", "home_base", "playoff_boost", "off_rtg_base",
            "def_rtg_base", "style_strong", "style_weak"]

    best_score = 999
    best_params = None
    best_result = None
    total_tested = 0

    # 分层搜索: 先粗搜，再细搜
    # 第一层: 减少组合数量
    for sw in PARAM_GRID["strength_weights"]:
        for hb in PARAM_GRID["home_base"]:
            for pb in PARAM_GRID["playoff_boost"]:
                for orb in PARAM_GRID["off_rtg_base"]:
                    for drb in PARAM_GRID["def_rtg_base"]:
                        for ss in PARAM_GRID["style_strong"]:
                            for sweak in PARAM_GRID["style_weak"]:
                                params = {
                                    "strength_weights": sw,
                                    "home_base": hb,
                                    "playoff_boost": pb,
                                    "off_rtg_base": orb,
                                    "def_rtg_base": drb,
                                    "style_strong": ss,
                                    "style_weak": sweak,
                                }
                                result = evaluate_params(all_team_data, all_games, params)
                                total_tested += 1

                                if result["combined"] < best_score:
                                    best_score = result["combined"]
                                    best_params = params
                                    best_result = result

    logger.info(f"  搜索完成: 测试 {total_tested} 组参数")
    return best_params, best_result


def save_snapshot(params: dict, result: dict, version: str = "v2"):
    """保存最优参数为 AlgorithmParamSnapshot"""
    with SessionLocal() as db:
        # 取消之前的 current
        existing = db.query(AlgorithmParamSnapshot).filter(
            AlgorithmParamSnapshot.is_current == 1
        ).all()
        for e in existing:
            e.is_current = 0

        snapshot = AlgorithmParamSnapshot(
            version=version,
            param_json=json.dumps(params, ensure_ascii=False),
            mae_score=result["combined"],
            is_current=1,
        )
        db.add(snapshot)
        db.commit()
        logger.info(f"  保存参数快照: {version}")


def run():
    logger.info("=" * 60)
    logger.info("系数优化开始")
    logger.info("=" * 60)

    # 加载所有数据
    all_team_data = {}
    all_games = []
    for base_s, val_s in TUNE_SEASONS:
        team_map = load_team_data_map(base_s)
        all_team_data.update(team_map)
        games = load_games(val_s)
        for g in games:
            g["_base_season"] = base_s
        all_games.extend(games)

    logger.info(f"加载 {len(all_team_data)} 支球队, {len(all_games)} 场比赛")

    # 默认参数基线
    default_params = {
        "strength_weights": (0.4, 0.3, 0.3),
        "home_base": 1.055,
        "playoff_boost": 1.08,
        "off_rtg_base": 112.0,
        "def_rtg_base": 112.0,
        "style_strong": 1.03,
        "style_weak": 0.95,
    }
    baseline = evaluate_params(all_team_data, all_games, default_params)
    logger.info(f"基线: MAE(总分)={baseline['mae_total']}, MAE(分差)={baseline['mae_diff']}, 胜率={baseline['win_acc']:.1%}")

    # 网格搜索
    logger.info("\n开始网格搜索...")
    best_params, best_result = grid_search(all_team_data, all_games)

    logger.info(f"\n最优参数:")
    for k, v in best_params.items():
        logger.info(f"  {k}: {v}")
    logger.info(f"最优结果: MAE(总分)={best_result['mae_total']}, MAE(分差)={best_result['mae_diff']}, 胜率={best_result['win_acc']:.1%}")

    # 改进幅度
    if baseline["combined"] > 0:
        improvement = (baseline["combined"] - best_result["combined"]) / baseline["combined"] * 100
        logger.info(f"改进: {improvement:.1f}% (综合指标)")

    # 保存最优参数
    save_snapshot(best_params, best_result)

    # 分赛季验证最优参数
    logger.info("\n分赛季验证:")
    for base_s, val_s in TUNE_SEASONS:
        team_map = load_team_data_map(base_s)
        games = load_games(val_s)
        result = evaluate_params(team_map, games, best_params)
        logger.info(f"  {val_s}: MAE(总分)={result['mae_total']}, MAE(分差)={result['mae_diff']}, 胜率={result['win_acc']:.1%}")

    # 保存完整报告
    report = {
        "baseline": baseline,
        "best_params": {k: str(v) for k, v in best_params.items()},
        "best_result": best_result,
        "improvement_pct": round((baseline["combined"] - best_result["combined"]) / max(baseline["combined"], 0.01) * 100, 1),
    }
    report_path = Path(__file__).resolve().parent.parent / "data" / "tuning_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"\n报告已保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
