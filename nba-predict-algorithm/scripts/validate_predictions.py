"""
预测系数验证脚本
用上赛季数据预测本赛季比赛，与真实结果对比
"""
import sys
import json
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, TeamData, Team, Player, PlayerData


# 验证赛季: (预测基础赛季, 验证赛季)
SEASON_PAIRS = [
    ("2022-23", "2023-24"),
    ("2023-24", "2024-25"),
    ("2024-25", "2025-26"),
]


@dataclass
class GamePrediction:
    game_id: int
    home_team_id: int
    away_team_id: int
    predict_home: int
    predict_away: int
    actual_home: int
    actual_away: int
    scene: str


def load_team_data_map(season: str) -> dict:
    """加载某赛季所有球队数据 -> {team_id: dict}"""
    with SessionLocal() as db:
        rows = db.query(TeamData).filter(TeamData.season == season).all()
        # 转为普通 dict 避免 ORM 对象脱离 session
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


def _get(td, key, default=0):
    """兼容 dict 和 ORM 对象"""
    if isinstance(td, dict):
        return td.get(key) or default
    return getattr(td, key, None) or default


def calc_strength_coeff(td) -> float:
    """实力系数"""
    win_pct = _get(td, "win_percentage", 0.5)
    off_rtg = _get(td, "offensive_rating", 110.0)
    def_rtg = _get(td, "defensive_rating", 110.0)

    win_factor = 0.8 + (win_pct * 0.4)
    off_factor = off_rtg / 112.0
    def_factor = 112.0 / max(def_rtg, 90.0)

    return win_factor * 0.4 + off_factor * 0.3 + def_factor * 0.3


def calc_home_coeff(td) -> float:
    """主场优势系数"""
    base = 1.055
    hw = _get(td, "home_wins", 0)
    hl = _get(td, "home_losses", 0)
    if hw and hl:
        total = hw + hl
        if total > 0:
            base = 1.03 + ((hw / total) * 0.05)
    return base


def calc_scene_coeff(is_playoff: int) -> float:
    """比赛场景系数"""
    return 1.08 if is_playoff else 1.0


def calc_style_matchup(home_td, away_td) -> float:
    """风格克制系数"""
    home_off = _get(home_td, "offensive_rating", 110.0)
    home_def = _get(home_td, "defensive_rating", 110.0)
    away_off = _get(away_td, "offensive_rating", 110.0)
    away_def = _get(away_td, "defensive_rating", 110.0)

    home_type = "进攻型" if home_off > home_def else "防守型"
    away_type = "进攻型" if away_off > away_def else "防守型"

    if home_type == "进攻型" and away_type == "防守型":
        three_pct = _get(away_td, "opponent_three_pct", 0.35)
        return 0.95 if three_pct < 0.34 else 1.03
    elif home_type == "防守型" and away_type == "进攻型":
        three_pct = _get(home_td, "three_percentage", 0.35)
        return 1.03 if three_pct > 0.38 else 0.97
    return 1.0


def predict_game(home_td, away_td, is_playoff: int) -> tuple:
    """预测单场比赛，返回 (predict_home, predict_away)"""
    home_sc = calc_strength_coeff(home_td)
    away_sc = calc_strength_coeff(away_td)
    home_c = calc_home_coeff(home_td)
    scene_c = calc_scene_coeff(is_playoff)
    style_c = calc_style_matchup(home_td, away_td)

    home_total = home_sc * home_c * scene_c * style_c
    away_total = away_sc * scene_c

    base_home = _get(home_td, "points_per_game", 110.0)
    base_away = _get(away_td, "points_per_game", 108.0)

    return round(base_home * home_total), round(base_away * away_total)


def validate_team_predictions(base_season: str, val_season: str) -> dict:
    """验证球队预测精度"""
    logger.info(f"验证: 基于 {base_season} 预测 {val_season}")

    team_data_map = load_team_data_map(base_season)
    logger.info(f"  加载 {len(team_data_map)} 支球队数据")

    with SessionLocal() as db:
        games_raw = db.query(GameRecord).filter(
            GameRecord.season == val_season,
            GameRecord.status == "FINISHED",
        ).all()
        # 提取为普通数据避免 ORM 脱离 session
        games = [{
            "game_id": g.game_id,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_playoff": g.is_playoff,
        } for g in games_raw]

    logger.info(f"  加载 {len(games)} 场比赛")

    predictions: list[GamePrediction] = []
    skipped = 0

    for g in games:
        home_td = team_data_map.get(g["home_team_id"])
        away_td = team_data_map.get(g["away_team_id"])
        if not home_td or not away_td:
            skipped += 1
            continue

        ph, pa = predict_game(home_td, away_td, g["is_playoff"])
        predictions.append(GamePrediction(
            game_id=g["game_id"],
            home_team_id=g["home_team_id"],
            away_team_id=g["away_team_id"],
            predict_home=ph,
            predict_away=pa,
            actual_home=g["home_score"],
            actual_away=g["away_score"],
            scene="季后赛" if g["is_playoff"] else "常规赛",
        ))

    if not predictions:
        return {"season": val_season, "error": "无有效预测"}

    # 计算指标
    total_mae = sum(abs(p.predict_home + p.predict_away - p.actual_home - p.actual_away) for p in predictions) / len(predictions)
    diff_mae = sum(abs((p.predict_home - p.predict_away) - (p.actual_home - p.actual_away)) for p in predictions) / len(predictions)

    # 胜负准确率
    correct = 0
    for p in predictions:
        predict_win = p.predict_home > p.predict_away
        actual_win = p.actual_home > p.actual_away
        if predict_win == actual_win:
            correct += 1
    win_acc = correct / len(predictions)

    # 分常规赛/季后赛
    regular = [p for p in predictions if p.scene == "常规赛"]
    playoff = [p for p in predictions if p.scene == "季后赛"]

    def calc_subset(subset):
        if not subset:
            return None
        t_mae = sum(abs(p.predict_home + p.predict_away - p.actual_home - p.actual_away) for p in subset) / len(subset)
        d_mae = sum(abs((p.predict_home - p.predict_away) - (p.actual_home - p.actual_away)) for p in subset) / len(subset)
        corr = sum(1 for p in subset if (p.predict_home > p.predict_away) == (p.actual_home > p.actual_away))
        return {
            "count": len(subset),
            "mae_total": round(t_mae, 2),
            "mae_diff": round(d_mae, 2),
            "win_accuracy": round(corr / len(subset), 4),
        }

    result = {
        "season": val_season,
        "base_season": base_season,
        "total_games": len(predictions),
        "skipped": skipped,
        "overall": {
            "mae_total": round(total_mae, 2),
            "mae_diff": round(diff_mae, 2),
            "win_accuracy": round(win_acc, 4),
        },
        "regular_season": calc_subset(regular),
        "playoffs": calc_subset(playoff),
    }

    logger.info(f"  总计 {len(predictions)} 场 | 跳过 {skipped} 场")
    logger.info(f"  MAE(总分): {result['overall']['mae_total']} | MAE(分差): {result['overall']['mae_diff']}")
    logger.info(f"  胜率准确度: {result['overall']['win_accuracy']:.1%}")

    return result


def validate_player_predictions(val_season: str) -> dict:
    """验证球员预测精度 (基于赛季场均数据对比)"""
    logger.info(f"验证球员预测: {val_season}")

    with SessionLocal() as db:
        # 获取有赛季数据的球员
        players = db.query(Player).filter(Player.status == 1).all()
        results = []
        for p in players:
            pd = db.query(PlayerData).filter(
                PlayerData.player_id == p.player_id,
                PlayerData.season == val_season,
            ).first()
            if not pd:
                continue

            # 预测系数
            all_star_c = 1.0
            if p.all_star_count:
                if p.all_star_count <= 2: all_star_c = 1.10
                elif p.all_star_count <= 5: all_star_c = 1.20
                elif p.all_star_count <= 8: all_star_c = 1.30
                else: all_star_c = 1.40

            veteran_c = 1.0
            if p.age:
                if p.age >= 36: veteran_c = 0.80
                elif p.age >= 33: veteran_c = 0.90
                elif p.age >= 30: veteran_c = 0.95

            injury_c = 1.0
            if p.injury_status == "RECOVERY": injury_c = 0.85
            elif p.injury_status == "INJURED": injury_c = 0.70

            stability_c = 1.0
            if pd.points_cv:
                if pd.points_cv < 0.20: stability_c = 1.0
                elif pd.points_cv < 0.30: stability_c = 0.97
                elif pd.points_cv < 0.40: stability_c = 0.93
                else: stability_c = 0.85

            total_c = all_star_c * veteran_c * injury_c * 1.0 * 1.0 * 1.0 * stability_c

            base_pts = pd.points_per_game or 10.0
            predict_pts = round(base_pts * total_c, 1)
            actual_pts = pd.points_per_game  # 用赛季场均作为"实际值"

            results.append({
                "player_id": p.player_id,
                "name": p.player_name,
                "position": p.position,
                "team_id": p.team_id,
                "predict_pts": predict_pts,
                "actual_pts": actual_pts,
                "total_coeff": round(total_c, 3),
                "fg_pct": pd.fg_percentage,
                "ts_pct": pd.true_shooting_pct,
            })

    if not results:
        return {"season": val_season, "error": "无球员数据"}

    # 按位置分组统计
    from collections import defaultdict
    by_pos = defaultdict(list)
    for r in results:
        by_pos[r["position"] or "UNK"].append(r)

    pos_stats = {}
    for pos, items in by_pos.items():
        mae = sum(abs(r["predict_pts"] - r["actual_pts"]) for r in items) / len(items)
        avg_coeff = sum(r["total_coeff"] for r in items) / len(items)
        pos_stats[pos] = {
            "count": len(items),
            "mae_pts": round(mae, 2),
            "avg_coeff": round(avg_coeff, 3),
        }

    overall_mae = sum(abs(r["predict_pts"] - r["actual_pts"]) for r in results) / len(results)

    logger.info(f"  球员总数: {len(results)}")
    logger.info(f"  整体 MAE(得分): {overall_mae:.2f}")
    for pos, stats in sorted(pos_stats.items()):
        logger.info(f"  {pos}: {stats['count']}人, MAE={stats['mae_pts']:.2f}, avg_coeff={stats['avg_coeff']:.3f}")

    return {
        "season": val_season,
        "total_players": len(results),
        "overall_mae_pts": round(overall_mae, 2),
        "by_position": pos_stats,
        "top_deviations": sorted(results, key=lambda x: abs(x["predict_pts"] - x["actual_pts"]), reverse=True)[:10],
    }


def run():
    logger.info("=" * 60)
    logger.info("预测系数验证开始")
    logger.info("=" * 60)

    all_results = {
        "team_validation": {},
        "player_validation": {},
    }

    # 球队预测验证
    for base_season, val_season in SEASON_PAIRS:
        result = validate_team_predictions(base_season, val_season)
        all_results["team_validation"][val_season] = result

    # 球员预测验证
    for _, val_season in SEASON_PAIRS:
        result = validate_player_predictions(val_season)
        all_results["player_validation"][val_season] = result

    # 汇总
    logger.info("")
    logger.info("=" * 60)
    logger.info("汇总报告")
    logger.info("=" * 60)

    for season, r in all_results["team_validation"].items():
        if "error" in r:
            logger.info(f"  {season}: {r['error']}")
            continue
        logger.info(f"  {season}: MAE(总分)={r['overall']['mae_total']}, MAE(分差)={r['overall']['mae_diff']}, 胜率={r['overall']['win_accuracy']:.1%}")

    for season, r in all_results["player_validation"].items():
        if "error" in r:
            logger.info(f"  {season} 球员: {r['error']}")
            continue
        logger.info(f"  {season} 球员: MAE(得分)={r['overall_mae_pts']}, 球员数={r['total_players']}")

    # 保存报告
    report_path = Path(__file__).resolve().parent.parent / "data" / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # 清理不可序列化的对象
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(i) for i in obj]
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        return str(obj)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(clean(all_results), f, ensure_ascii=False, indent=2)

    logger.info(f"\n报告已保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
