"""
预测分析报告生成

数据源：data/espn_cache/boxscore_cache.json（5,156 场逐场球员技术统计）

流程：
  1. 按截止日期取两队最近的比赛（game_record.nba_game_id = 'espn_<id>'）
  2. 从缓存中取出每场的球员技术统计
  3. 计算每名球员的单场 Game Score（Hollinger 综合评分）
  4. 以个人赛季基线为参照，计算近 N 场滚动均值相对基线的 z 值
  5. 按出场时间加权聚合为球队状态指数
  6. 挑出最显著的信号，组织成中文报告

时点安全：所有窗口都按比赛日期回溯，只使用截止日期之前的比赛，
         因此这段逻辑也可以直接用于历史比赛的回溯分析。
"""
import json
import math
from collections import defaultdict
from typing import Optional

from loguru import logger

from app.db.database import SessionLocal
from app.db.models import GameRecord, Team
from config.settings import DATA_DIR

WINDOW = 5                 # 近期窗口长度
BASELINE_LIMIT = 20        # 基线样本上限（最近 20 场）
MIN_BASELINE_GAMES = 3     # 计算个人基线所需的最少出场数
MIN_AVG_MINUTES = 10.0     # 低于此平均出场时间的球员不参与检测
MIN_STD = 0.5              # 个人波动过小时 z 值无意义
Z_HOT = 1.0                # 判定「火热」的 z 阈值
Z_COLD = -1.0              # 判定「低迷」的 z 阈值

_cache: Optional[dict] = None


# ---------------- 数据加载 ----------------

def _load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    path = DATA_DIR / "espn_cache" / "boxscore_cache.json"
    if not path.exists():
        logger.warning(f"boxscore 缓存不存在，预测报告将跳过球员状态检测: {path}")
        _cache = {}
        return _cache
    with open(path, encoding="utf-8") as f:
        _cache = json.load(f)
    logger.info(f"已加载 boxscore 缓存 {len(_cache)} 场")
    return _cache


# ---------------- 指标计算 ----------------

def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _made_attempted(value) -> tuple:
    """'3-5' → (3, 5)"""
    try:
        made, attempted = str(value).split("-")
        return int(made), int(attempted)
    except (AttributeError, ValueError):
        return 0, 0


def game_score(stats: dict) -> float:
    """Hollinger 单场综合评分"""
    pts = _to_float(stats.get("PTS"))
    fgm, fga = _made_attempted(stats.get("FG"))
    ftm, fta = _made_attempted(stats.get("FT"))
    oreb = _to_float(stats.get("OREB"))
    dreb = _to_float(stats.get("DREB"))
    stl = _to_float(stats.get("STL"))
    ast = _to_float(stats.get("AST"))
    blk = _to_float(stats.get("BLK"))
    pf = _to_float(stats.get("PF"))
    tov = _to_float(stats.get("TO"))
    return (pts
            + 0.4 * fgm - 0.7 * fga
            - 0.4 * (fta - ftm)
            + 0.7 * oreb + 0.3 * dreb
            + stl + 0.7 * ast + 0.7 * blk
            - 0.4 * pf - tov)


def _mean(values) -> float:
    return sum(values) / len(values) if values else 0.0


def _pstdev(values) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))


# ---------------- 球队状态检测 ----------------

def _team_meta(team_id: int) -> tuple:
    with SessionLocal() as db:
        team = db.query(Team).filter(Team.team_id == team_id).first()
        if not team:
            return None, None
        return team.team_name, team.abbreviation


def _recent_games(team_id: int, before_date=None, limit: int = BASELINE_LIMIT) -> list:
    with SessionLocal() as db:
        query = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED",
            GameRecord.nba_game_id.like("espn_%"),
            (GameRecord.home_team_id == team_id) | (GameRecord.away_team_id == team_id),
        )
        if before_date is not None:
            query = query.filter(GameRecord.game_date < before_date)
        rows = query.order_by(GameRecord.game_date.desc()).limit(limit).all()
        return [(r.nba_game_id.replace("espn_", ""), r.game_date) for r in rows]


def analyze_team(team_id: int, before_date=None) -> dict:
    """返回球队的球员状态检测结果：信号列表 + 球队状态指数"""
    team_name, abbr = _team_meta(team_id)
    if not abbr:
        return {"team_name": team_name, "signals": [], "index": 0.0}

    cache = _load_cache()
    games = _recent_games(team_id, before_date)
    if not games:
        return {"team_name": team_name, "signals": [], "index": 0.0, "stale": False}

    # 只统计确实有 boxscore 的比赛：缓存缺场时不能把「没有数据」当成「没有出场」
    available = [(espn_id, gdate) for espn_id, gdate in games if espn_id in cache]
    if not available:
        return {"team_name": team_name, "signals": [], "index": 0.0, "stale": True}

    # 最近一场比赛不在缓存里（间隔超过 14 天）说明数据陈旧，缺阵判据不可信
    stale = (games[0][1] - available[0][1]).days > 14

    # player_name -> [(game_index, game_score, minutes)]，game_index 0 表示缓存中最近一场
    per_player = defaultdict(list)
    for idx, (espn_id, _) in enumerate(available):
        block = cache[espn_id]
        team_block = next((b for b in block if b.get("team_abbr") == abbr), None)
        if not team_block:
            continue
        for player in team_block.get("players", []):
            stats = player.get("stats") or {}
            minutes = _to_float(stats.get("MIN"))
            if minutes <= 0:
                continue
            per_player[player.get("name")].append((idx, game_score(stats), minutes))

    players = []
    for name, records in per_player.items():
        if len(records) < MIN_BASELINE_GAMES:
            continue
        avg_minutes = _mean([r[2] for r in records])
        if avg_minutes < MIN_AVG_MINUTES:
            continue

        scores = [r[1] for r in records]
        baseline = _mean(scores)
        std = _pstdev(scores)
        recent = _mean([r[1] for r in records if r[0] < WINDOW])
        z = (recent - baseline) / std if std > MIN_STD else 0.0

        last_index = min(r[0] for r in records)
        players.append({
            "name": name,
            "avg_minutes": round(avg_minutes, 1),
            "baseline": round(baseline, 1),
            "recent": round(recent, 1),
            "z": round(z, 2),
            # 数据陈旧时不推断缺阵，避免把缓存缺场误判为伤停
            "absent": (not stale) and last_index >= 2
                      and len(records) >= MIN_BASELINE_GAMES,
            "missed_games": last_index,
        })

    if not players:
        return {"team_name": team_name, "signals": [], "index": 0.0, "stale": stale}

    # 球队状态指数：按出场时间加权
    active = [p for p in players if not p["absent"]]
    total_minutes = sum(p["avg_minutes"] for p in active)
    index = (sum(p["z"] * p["avg_minutes"] for p in active) / total_minutes
             if total_minutes else 0.0)

    signals = []
    hot = [p for p in active if p["z"] >= Z_HOT]
    if hot:
        signals.append({"type": "hot", **max(hot, key=lambda p: p["z"])})
    cold = [p for p in active if p["z"] <= Z_COLD]
    if cold:
        signals.append({"type": "cold", **min(cold, key=lambda p: p["z"])})
    absent = [p for p in players if p["absent"]]
    if absent:
        signals.append({"type": "absent", **max(absent, key=lambda p: p["avg_minutes"])})

    return {
        "team_name": team_name,
        "signals": signals,
        "index": round(index, 2),
        "player_count": len(players),
        "stale": stale,
    }


# ---------------- 报告文本 ----------------

def _describe_team(state: dict) -> str:
    team_name = state.get("team_name") or "该队"
    signals = {s["type"]: s for s in state.get("signals", [])}

    parts = []
    if "hot" in signals:
        p = signals["hot"]
        parts.append(f"「{p['name']}」近 {WINDOW} 场状态火热"
                     f"（Game Score {p['recent']:.1f}，高于个人基线 {p['z']:.1f} 个标准差）")
    if "absent" in signals:
        p = signals["absent"]
        parts.append(f"「{p['name']}」（场均 {p['avg_minutes']:.0f} 分钟）"
                     f"已连续缺阵 {p['missed_games']} 场")
    if "cold" in signals:
        p = signals["cold"]
        parts.append(f"「{p['name']}」近 {WINDOW} 场表现低迷"
                     f"（Game Score {p['recent']:.1f}，低于个人基线 {abs(p['z']):.1f} 个标准差）")

    if not parts:
        return f"{team_name}近期阵容与状态无显著变化"
    return f"{team_name}方面，" + "；".join(parts)


def generate_report(home_team_id: int,
                    away_team_id: int,
                    before_date=None,
                    prediction: Optional[dict] = None) -> dict:
    """
    生成预测分析报告。

    :param before_date: 截止日期。预测未来比赛传 None；分析历史比赛时传该场比赛日期，
                        以保证不使用赛后信息。
    :param prediction: 可选，{home_score, away_score, win_prob}，用于生成结论句
    """
    home = analyze_team(home_team_id, before_date)
    away = analyze_team(away_team_id, before_date)

    sentences = [f"{_describe_team(home)}。", f"{_describe_team(away)}。"]

    gap = home["index"] - away["index"]
    if abs(gap) >= 0.30:
        higher = home["team_name"] if gap > 0 else away["team_name"]
        sentences.append(
            f"球员状态指数方面{higher}更高"
            f"（{home['team_name']} {home['index']:+.2f} : "
            f"{away['team_name']} {away['index']:+.2f}），"
            f"该项仅反映球员近期表现，与模型综合预测可能不一致。"
        )

    if prediction and prediction.get("home_score") is not None:
        home_score = prediction["home_score"]
        away_score = prediction["away_score"]
        prob = prediction.get("win_prob")
        prob_text = f"，主胜概率 {prob:.0%}" if prob is not None else ""
        if home_score == away_score:
            verdict = "双方战平"
        elif home_score > away_score:
            verdict = f"{home['team_name']}占优"
        else:
            verdict = f"{away['team_name']}占优"
        sentences.append(
            f"综合球队统计与球员状态，模型预测比分 {home_score}:{away_score}{prob_text}，{verdict}。"
        )

    return {
        "text": "".join(sentences),
        "home": home,
        "away": away,
        "window": WINDOW,
        "method": "Game Score 滚动均值 z 值检测，按出场时间加权",
    }
