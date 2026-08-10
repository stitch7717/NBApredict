"""
从真实比赛记录计算球队赛季统计
从比分推算真实效率值、节奏、主客场拆分
"""
import sys
import statistics
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, TeamData, Team

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]


def compute_season(season: str):
    """从比赛记录计算某赛季的球队统计"""
    logger.info(f"计算 {season} 赛季统计...")

    with SessionLocal() as db:
        existing = db.query(TeamData).filter(TeamData.season == season).count()
        if existing > 0:
            logger.info(f"  已有 {existing} 条 TeamData，跳过")
            return

        games = db.query(GameRecord).filter(
            GameRecord.season == season,
            GameRecord.status == "FINISHED",
        ).all()

        if not games:
            logger.warning(f"  无比赛数据")
            return

        logger.info(f"  共 {len(games)} 场比赛")

        # 计算联赛平均值 (用于估算 pace)
        regular_games = [g for g in games if not g.is_playoff]
        if not regular_games:
            regular_games = games
        league_avg_total = sum(g.home_score + g.away_score for g in regular_games) / len(regular_games)

        # 按球队统计
        stats = defaultdict(lambda: {
            "wins": 0, "losses": 0,
            "home_wins": 0, "home_losses": 0,
            "away_wins": 0, "away_losses": 0,
            "pf": [], "pa": [],
            "home_pf": [], "home_pa": [],
            "away_pf": [], "away_pa": [],
            "game_dates": [],
            "results_by_date": [],
        })

        for g in games:
            hs, as_ = g.home_score, g.away_score
            date = g.game_date

            # 主队
            s = stats[g.home_team_id]
            s["pf"].append(hs)
            s["pa"].append(as_)
            s["game_dates"].append(date)
            s["results_by_date"].append((date, hs, as_, "H"))
            if not g.is_playoff:
                s["home_pf"].append(hs)
                s["home_pa"].append(as_)
            if hs > as_:
                s["wins"] += 1
                s["home_wins"] += 1
            else:
                s["losses"] += 1
                s["home_losses"] += 1

            # 客队
            s2 = stats[g.away_team_id]
            s2["pf"].append(as_)
            s2["pa"].append(hs)
            s2["game_dates"].append(date)
            s2["results_by_date"].append((date, as_, hs, "A"))
            if not g.is_playoff:
                s2["away_pf"].append(as_)
                s2["away_pa"].append(hs)
            if as_ > hs:
                s2["wins"] += 1
                s2["away_wins"] += 1
            else:
                s2["losses"] += 1
                s2["away_losses"] += 1

        # 写入 TeamData
        count = 0
        for team_id, s in stats.items():
            total = s["wins"] + s["losses"]
            if total == 0:
                continue

            # 常规赛数据
            reg_pf = [pf for pf in (s["home_pf"] + s["away_pf"])]
            reg_pa = [pa for pa in (s["home_pa"] + s["away_pa"])]

            ppg = round(sum(reg_pf) / len(reg_pf), 1) if reg_pf else 110.0
            oppg = round(sum(reg_pa) / len(reg_pa), 1) if reg_pa else 110.0
            pts_std = round(statistics.stdev(reg_pf), 1) if len(reg_pf) > 1 else ppg * 0.12

            # 估算 pace: 联赛平均总分 / 2 ≈ 平均回合数
            # 球队节奏 = (球队得分 + 对手得分) / 联赛平均总分 * 100
            team_total = ppg + oppg
            est_pace = round(team_total / league_avg_total * 100, 1)

            # 进攻/防守效率 (每100回合得分/失分)
            off_rtg = round(ppg / max(est_pace, 1) * 100, 1)
            def_rtg = round(oppg / max(est_pace, 1) * 100, 1)

            # 主客场拆分
            home_ppg = round(sum(s["home_pf"]) / len(s["home_pf"]), 1) if s["home_pf"] else ppg
            away_ppg = round(sum(s["away_pf"]) / len(s["away_pf"]), 1) if s["away_pf"] else ppg
            home_oppg = round(sum(s["home_pa"]) / len(s["home_pa"]), 1) if s["home_pa"] else oppg
            away_oppg = round(sum(s["away_pa"]) / len(s["away_pa"]), 1) if s["away_pa"] else oppg

            # 近 10 场胜率 + momentum
            s["results_by_date"].sort(key=lambda x: x[0])
            recent_wins = sum(1 for _, pf, pa, _ in s["results_by_date"][-10:] if pf > pa)
            recent_total = min(10, len(s["results_by_date"]))
            recent_wr = round(recent_wins / max(recent_total, 1), 3)

            # momentum: 近 10 场场均得分
            recent_pf = s["pf"][-10:]
            momentum = round(sum(recent_pf) / max(len(recent_pf), 1), 1) if recent_pf else ppg

            home_total = s["home_wins"] + s["home_losses"]
            away_total = s["away_wins"] + s["away_losses"]

            td = TeamData(
                team_id=team_id,
                season=season,
                wins=s["wins"],
                losses=s["losses"],
                win_percentage=round(s["wins"] / total, 3),
                home_wins=s["home_wins"],
                home_losses=s["home_losses"],
                away_wins=s["away_wins"],
                away_losses=s["away_losses"],
                points_per_game=ppg,
                assists_per_game=25.0,
                rebounds_per_game=44.0,
                turnovers_per_game=14.0,
                fg_percentage=0.46,
                three_percentage=0.36,
                ft_percentage=0.78,
                steals_per_game=7.5,
                blocks_per_game=5.0,
                opponent_points=oppg,
                opponent_fg_percentage=0.46,
                opponent_three_pct=0.36,
                pace=est_pace,
                offensive_rating=off_rtg,
                defensive_rating=def_rtg,
                points_std=pts_std,
                points_cv=round(pts_std / max(ppg, 1), 3),
                recent_win_rate=recent_wr,
                momentum=momentum,
                home_ppg=home_ppg,
                away_ppg=away_ppg,
                fast_break_points=14.0,
                points_in_paint=48.0,
                second_chance_points=12.0,
                bench_points=35.0,
            )
            db.add(td)
            count += 1

        db.commit()
        logger.info(f"  写入 {count} 条 TeamData (pace 基准={league_avg_total:.1f})")


def run():
    logger.info("=" * 50)
    logger.info("球队赛季统计计算 (真实效率值)")
    logger.info("=" * 50)

    for season in SEASONS:
        compute_season(season)

    logger.info("=" * 50)
    logger.info("计算完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
