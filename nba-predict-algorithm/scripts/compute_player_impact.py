"""
球员角色分类与影响力计算 (v2: 15角色 + 6维度)

角色分类 (15类):
  核心: ball_handler / defensive_anchor / scorer / two_way / stretch_big / rim_protector
  替补: floor_general / sixth_man / three_and_d / connector / energy_big /
        microwave_scorer / spot_up_shooter / veteran_stabilizer / role_player

影响力维度 (6维):
  进攻影响力 / 防守影响力 / 球队依赖度 / 稳定性 / 组织串联值 / 经验值
"""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, TeamData


def _is_starter(d: PlayerData) -> bool:
    """判断是否首发 (首发出场占比 ≥ 70%)"""
    gp = d.games_played or 0
    gs = d.games_started or 0
    if gp < 10:
        return False
    return gs / gp >= 0.7


def _classify_role(p: Player, d: PlayerData) -> str:
    """
    根据统计数据判断球员角色 (15类)

    优先级: 内线特殊 → 核心角色 → 替补细分 → 兜底
    """
    ast_pct = d.assist_pct or 0
    usg = d.usage_rate or 0
    blk_pct = d.block_pct or 0
    stl_pct = d.steal_pct or 0
    ppg = d.points_per_game or 0
    per = d.per or 0
    drtg = d.defensive_rating or 110.0
    ortg = d.offensive_rating or 110.0
    three_pct = d.three_percentage or 0
    three_att = d.three_attempted_per_game or 0
    reb_pct = d.rebound_pct or 0
    tov_pct = d.turnover_pct or 99.0
    ts_pct = d.true_shooting_pct or 0
    mpg = d.minutes_per_game or 0
    cv = d.points_cv or 0
    exp = p.experience or 0

    is_big = (p.position or "").upper() in ("C", "PF", "C-PF", "PF-C")
    is_guard = (p.position or "").upper() in ("PG", "SG", "PG-SG", "SG-PG")
    starter = _is_starter(d)

    # AST/TO 比率 (避免除零)
    ast_to = (ast_pct / tov_pct) if tov_pct > 0 and ast_pct > 0 else 0

    # ── 内线特殊角色 ──────────────────────────────────────
    if is_big and blk_pct >= 5.0:
        return "rim_protector"
    if is_big and three_pct >= 0.33 and three_att >= 2.0:
        return "stretch_big"
    if is_big and reb_pct >= 15.0 and blk_pct >= 2.0 and mpg >= 18:
        return "energy_big"

    # ── 核心角色 (首发级别) ────────────────────────────────
    # 持球核心: 高助攻率 + 高使用率
    if ast_pct >= 25.0 and usg >= 20.0:
        return "ball_handler"
    # 防守核心: 高抢断/盖帽 + 防守效率好
    if (stl_pct >= 2.0 or blk_pct >= 3.0) and drtg <= 108.0:
        return "defensive_anchor"
    # 攻防一体: 进攻效率好 + 防守效率好
    if per >= 18.0 and drtg <= 108.0 and ortg >= 112.0:
        return "two_way"
    # 得分手: 高得分 + 高使用率
    if ppg >= 20.0 and usg >= 25.0:
        return "scorer"

    # ── 替补细分角色 ──────────────────────────────────────
    # 替补指挥官: 非首发 + 高助攻 + 低失误 (典型: 康利、保罗)
    if not starter and ast_pct >= 20.0 and tov_pct <= 15.0:
        return "floor_general"
    # 第六人: 非首发 + 高出场 + 高得分
    if not starter and mpg >= 24 and ppg >= 14:
        return "sixth_man"
    # 3D球员: 高三分 + 高防守
    if three_pct >= 0.36 and three_att >= 4.0 and stl_pct >= 1.5 and drtg <= 109.0:
        return "three_and_d"
    # 组织串联: 不占球权但能组织 (高助攻低使用)
    if ast_pct >= 15.0 and ast_to >= 2.5 and usg <= 20.0:
        return "connector"
    # 微波得分手: 替补 + 高效 + 高波动 (典型: 克拉克森)
    if not starter and ppg >= 10 and cv >= 0.35 and ts_pct >= 0.55:
        return "microwave_scorer"
    # 定点射手: 高三分出手 + 低使用率
    if three_pct >= 0.37 and three_att >= 5.0 and usg <= 18.0:
        return "spot_up_shooter"
    # 老将稳定器: 高经验 + 低失误 + 有一定产出
    if exp >= 10 and per >= 12 and tov_pct <= 12 and (starter or mpg >= 20):
        return "veteran_stabilizer"

    # ── 兜底 ─────────────────────────────────────────────
    return "role_player"


def _calc_offensive_impact(d: PlayerData, team_ppg: float) -> float:
    """进攻影响力 (0-1): 得分占比 × 效率 × 使用率"""
    ppg = d.points_per_game or 0
    ts = d.true_shooting_pct or 0.55
    usg = d.usage_rate or 10.0

    score_share = ppg / max(team_ppg, 80.0)
    efficiency_factor = min(1.2, ts / 0.57) if ts > 0 else 1.0
    usg_factor = min(1.3, usg / 25.0) if usg > 0 else 1.0

    raw = score_share * efficiency_factor * usg_factor
    return min(0.95, max(0.0, raw))


def _calc_defensive_impact(d: PlayerData, team_drtg: float) -> float:
    """防守影响力 (0-1): 抢断/盖帽/防守效率/篮板"""
    stl_pct = d.steal_pct or 0
    blk_pct = d.block_pct or 0
    drtg = d.defensive_rating or 110.0
    reb_pct = d.rebound_pct or 0

    stl_factor = min(2.0, stl_pct / 1.5) if stl_pct > 0 else 0.5
    blk_factor = min(2.0, blk_pct / 2.5) if blk_pct > 0 else 0.5
    drtg_factor = min(1.3, team_drtg / max(drtg, 90.0)) if team_drtg > 0 else 1.0
    reb_factor = min(1.5, reb_pct / 10.0) if reb_pct > 0 else 0.5

    raw = stl_factor * 0.25 + blk_factor * 0.25 + drtg_factor * 0.30 + reb_factor * 0.20
    return min(0.95, max(0.0, raw * 0.5))


def _calc_team_dependency(d: PlayerData, team_data: TeamData) -> float:
    """球队依赖度 (0-1): 该球员产出占球队总产出的比例"""
    if not team_data:
        return 0.1

    ppg = d.points_per_game or 0
    team_ppg = team_data.points_per_game or 110.0
    ast = d.assists_per_game or 0
    team_ast = team_data.assists_per_game or 25.0
    reb = d.rebounds_per_game or 0
    team_reb = team_data.rebounds_per_game or 44.0

    score_dep = ppg / max(team_ppg, 80.0)
    ast_dep = ast / max(team_ast, 15.0)
    reb_dep = reb / max(team_reb, 30.0)

    raw = score_dep * 0.50 + ast_dep * 0.25 + reb_dep * 0.25
    return min(0.50, max(0.0, raw))


def _calc_stability_score(d: PlayerData) -> float:
    """
    稳定性 (0-1)
    低波动(低 CV) + 高出勤 = 高稳定
    稳定球员缺阵对球队影响更大
    """
    cv = d.points_cv or 0.3       # 变异系数, 越低越稳定
    gp = d.games_played or 0
    # 出勤率 (常规赛 82 场)
    attendance = min(1.0, gp / 75.0) if gp > 0 else 0.5

    # CV 转换: CV=0 → 1.0, CV=0.5 → 0.5
    cv_score = max(0.0, 1.0 - cv)

    return min(1.0, max(0.0, cv_score * 0.6 + attendance * 0.4))


def _calc_connector_score(d: PlayerData) -> float:
    """
    组织串联值 (0-1)
    不占用球权但能组织进攻的能力
    高助攻率 + 高助攻失误比 + 低使用率 = 高串联值
    典型: 德雷蒙德·格林、约什·哈特
    """
    ast_pct = d.assist_pct or 0
    tov_pct = d.turnover_pct or 99.0
    usg = d.usage_rate or 25.0

    # 助攻失误比
    ast_to = (ast_pct / tov_pct) if tov_pct > 0 and ast_pct > 0 else 0

    # 助攻贡献 (联盟平均约 15%)
    ast_factor = min(2.0, ast_pct / 15.0) if ast_pct > 0 else 0

    # 助攻失误比贡献 (联盟平均约 1.8)
    to_factor = min(2.0, ast_to / 1.8) if ast_to > 0 else 0

    # 低使用率加权 (越低越说明是"隐形串联")
    usg_penalty = max(0.3, 1.0 - (usg / 30.0)) if usg > 0 else 1.0

    raw = ast_factor * 0.40 + to_factor * 0.35 + usg_penalty * 0.25
    return min(1.0, max(0.0, raw))


def _calc_veteran_score(p: Player, d: PlayerData) -> float:
    """
    经验值 (0-1)
    老将的隐性价值: 临场判断、关键球、更衣室领导力
    经验 × 效率 的非线性组合
    """
    exp = p.experience or 0
    per = d.per or 0
    tov_pct = d.turnover_pct or 99.0

    # 经验贡献 (对数增长, 10年≈0.72, 15年≈0.88)
    exp_factor = math.log(max(exp + 1, 1)) / math.log(20) if exp > 0 else 0

    # 效率贡献 (PER 归一化, 联盟平均约 15)
    per_factor = min(1.0, per / 20.0) if per > 0 else 0

    # 低失误加权 (老将少失误 = 更可靠)
    tov_bonus = max(0.5, 1.0 - (tov_pct / 20.0)) if tov_pct > 0 else 0.5

    raw = exp_factor * 0.45 + per_factor * 0.35 + tov_bonus * 0.20
    return min(1.0, max(0.0, raw))


def _calc_impact_score(
    off: float, deff: float, dep: float,
    stab: float, conn: float, vet: float,
    role: str
) -> float:
    """
    综合影响力评分 (0-100)
    基础 = (进攻 + 防守) × 依赖度
    加成 = 稳定性 + 组织串联 + 经验
    """
    # 核心贡献
    base = (off + deff) * dep * 100

    # 隐性贡献 (不依赖球队占比, 直接加分)
    bonus = (stab * 5 + conn * 8 + vet * 6)  # 最多 +19

    # 角色权重
    role_weight = {
        "ball_handler": 1.15,
        "defensive_anchor": 1.10,
        "scorer": 1.10,
        "two_way": 1.20,
        "stretch_big": 1.05,
        "rim_protector": 1.05,
        "floor_general": 1.12,      # 替补指挥官
        "sixth_man": 1.08,
        "three_and_d": 1.06,
        "connector": 1.10,          # 组织串联
        "energy_big": 1.02,
        "microwave_scorer": 1.03,
        "spot_up_shooter": 1.02,
        "veteran_stabilizer": 1.08,  # 老将稳定器
        "role_player": 1.00,
    }.get(role, 1.00)

    return min(100.0, round((base + bonus) * role_weight, 1))


def compute_season(season: str):
    """计算一个赛季所有球员的角色和影响力"""
    logger.info(f"计算球员影响力: {season}")

    with SessionLocal() as db:
        results = db.query(Player, PlayerData).join(
            PlayerData, Player.player_id == PlayerData.player_id
        ).filter(
            Player.status == 1,
            PlayerData.season == season,
            PlayerData.games_played >= 10,
        ).all()

        if not results:
            logger.warning(f"无球员数据: {season}")
            return

        # 按球队分组
        team_players = {}
        for p, d in results:
            tid = d.team_id or p.team_id
            if tid not in team_players:
                team_players[tid] = []
            team_players[tid].append((p, d))

        # 加载球队数据
        team_data_map = {}
        for td in db.query(TeamData).filter(TeamData.season == season).all():
            team_data_map[td.team_id] = td

        updated = 0
        for tid, players in team_players.items():
            team_data = team_data_map.get(tid)
            team_ppg = team_data.points_per_game if team_data else 110.0
            team_drtg = team_data.defensive_rating if team_data else 110.0

            for p, d in players:
                role = _classify_role(p, d)
                off = _calc_offensive_impact(d, team_ppg)
                deff = _calc_defensive_impact(d, team_drtg)
                dep = _calc_team_dependency(d, team_data)
                stab = _calc_stability_score(d)
                conn = _calc_connector_score(d)
                vet = _calc_veteran_score(p, d)
                score = _calc_impact_score(off, deff, dep, stab, conn, vet, role)

                p.player_role = role
                p.impact_score = score
                p.offensive_impact = round(off, 3)
                p.defensive_impact = round(deff, 3)
                p.team_dependency = round(dep, 3)
                p.stability_score = round(stab, 3)
                p.connector_score = round(conn, 3)
                p.veteran_score = round(vet, 3)
                updated += 1

        db.commit()

        # 统计角色分布
        role_counts = {}
        for p, _ in results:
            r = p.player_role or "unknown"
            role_counts[r] = role_counts.get(r, 0) + 1

        logger.info(f"球员影响力计算完成: {updated} 人")
        logger.info(f"角色分布:")
        for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {role}: {count}")

        # 影响力 Top 10
        results_sorted = sorted(results, key=lambda x: x[0].impact_score or 0, reverse=True)
        logger.info("影响力 Top 10:")
        for p, d in results_sorted[:10]:
            logger.info(
                f"  {p.player_name}: role={p.player_role}, impact={p.impact_score}, "
                f"off={p.offensive_impact}, def={p.defensive_impact}, dep={p.team_dependency}, "
                f"stab={p.stability_score}, conn={p.connector_score}, vet={p.veteran_score}"
            )

        # 替补指挥官 / 老将稳定器 示例
        floor_generals = [(p, d) for p, d in results if p.player_role == "floor_general"]
        if floor_generals:
            floor_generals.sort(key=lambda x: x[0].impact_score or 0, reverse=True)
            logger.info(f"替补指挥官 ({len(floor_generals)}):")
            for p, d in floor_generals[:5]:
                logger.info(
                    f"  {p.player_name}: impact={p.impact_score}, "
                    f"conn={p.connector_score}, ast%={d.assist_pct:.1f}, tov%={d.turnover_pct:.1f}"
                )

        veterans = [(p, d) for p, d in results if p.player_role == "veteran_stabilizer"]
        if veterans:
            veterans.sort(key=lambda x: x[0].impact_score or 0, reverse=True)
            logger.info(f"老将稳定器 ({len(veterans)}):")
            for p, d in veterans[:5]:
                logger.info(
                    f"  {p.player_name}: impact={p.impact_score}, "
                    f"vet={p.veteran_score}, exp={p.experience}, per={d.per:.1f}"
                )


def run():
    """计算所有赛季的球员影响力"""
    seasons = ["2022-23", "2023-24", "2024-25", "2025-26"]
    for season in seasons:
        try:
            compute_season(season)
        except Exception as e:
            logger.error(f"计算 {season} 球员影响力失败: {e}")


if __name__ == "__main__":
    run()
