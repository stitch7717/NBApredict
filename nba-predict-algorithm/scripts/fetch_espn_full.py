"""
从 ESPN API 爬取完整 boxscore 数据，计算高阶指标，写入数据库
覆盖 4 个赛季 (2022-23 ~ 2025-26)
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, Team, TeamData, GameRecord

# 配置
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
REQUEST_DELAY = 1.5  # 请求间隔(秒)
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "espn_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ESPN 缩写修正
ESPN_ABBR_FIX = {
    "GS": "GSW", "NO": "NOP", "UTAH": "UTA",
    "WSH": "WAS", "NY": "NYK", "SA": "SAS",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_json(url: str, retries: int = 3) -> dict:
    """请求 ESPN API，指数退避重试"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
            else:
                logger.debug(f"请求失败: {url[:80]}... {e}")
    return {}


def get_team_abbr_map() -> tuple:
    """获取 (abbreviation -> team_id, team_id -> abbreviation) 映射"""
    with SessionLocal() as db:
        teams = db.query(Team).all()
        abbr_to_id = {t.abbreviation: t.team_id for t in teams}
        id_to_abbr = {t.team_id: t.abbreviation for t in teams}
        for espn_abbr, db_abbr in ESPN_ABBR_FIX.items():
            if db_abbr in abbr_to_id:
                abbr_to_id[espn_abbr] = abbr_to_id[db_abbr]
                id_to_abbr[abbr_to_id[db_abbr]] = espn_abbr
        return abbr_to_id, id_to_abbr


def get_espn_player_map() -> dict:
    """获取 espn_id -> player 映射"""
    with SessionLocal() as db:
        players = db.query(Player).all()
        return {p.nba_id: p for p in players}


def parse_fg(val: str) -> tuple:
    """解析 '7-12' 格式的投篮数据"""
    if not val or "-" not in str(val):
        return 0, 0, 0.0
    parts = str(val).split("-")
    try:
        made, att = int(parts[0]), int(parts[1])
        pct = round(made / att, 3) if att > 0 else 0.0
        return made, att, pct
    except (ValueError, IndexError):
        return 0, 0, 0.0


def parse_stat(val, default=0.0) -> float:
    """解析数值，处理 DNP/- 等情况"""
    if not val or val == "-" or val == "DNP":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def fetch_boxscore_for_game(espn_game_id: str) -> list:
    """获取单场比赛的 boxscore 数据，返回 [{team_abbr, players}] 列表"""
    url = f"{ESPN_SUMMARY}?event={espn_game_id}"
    data = fetch_json(url)
    if not data:
        return None

    bs = data.get("boxscore", {})
    players_section = bs.get("players", [])
    if len(players_section) != 2:
        return None

    result = []
    for team_data in players_section:
        team_abbr = team_data.get("team", {}).get("abbreviation", "")
        team_players = []

        for stat_group in team_data.get("statistics", []):
            labels = stat_group.get("labels", [])
            for ath_entry in stat_group.get("athletes", []):
                ath = ath_entry.get("athlete", {})
                espn_id = str(ath.get("id", ""))
                stats = ath_entry.get("stats", [])
                if not espn_id or not stats or len(stats) != len(labels):
                    continue
                stat_dict = dict(zip(labels, stats))
                team_players.append({
                    "espn_id": espn_id,
                    "name": ath.get("displayName", ""),
                    "team_abbr": team_abbr,
                    "stats": stat_dict,
                })

        result.append({"team_abbr": team_abbr, "players": team_players})

    return result


def compute_player_advanced(pts, fgm, fga, fg3m, fg3a, ftm, fta,
                             reb, oreb, dreb, ast, stl, blk, tov, pf, min_val,
                             team_fga, team_fta, team_tov, team_oreb,
                             team_fgm, team_reb, opp_reb, team_min):
    """从单场 boxscore 计算球员高阶指标"""
    # TS%
    ts_denom = 2 * (fga + 0.44 * fta)
    ts_pct = round(pts / ts_denom, 3) if ts_denom > 0 else 0.0

    # eFG%
    efg_pct = round((fgm + 0.5 * fg3m) / fga, 3) if fga > 0 else 0.0

    # USG% (近似)
    if min_val > 0 and team_fga > 0:
        usg_num = (fga + 0.44 * fta + tov) * (team_min / 5)
        usg_denom = min_val * (team_fga + 0.44 * team_fta + team_tov)
        usg_pct = round(usg_num / usg_denom * 100, 1) if usg_denom > 0 else 0.0
    else:
        usg_pct = 0.0

    # AST%
    if min_val > 0 and team_fgm > 0:
        ast_pct_num = ast * (team_min / 5)
        ast_pct_denom = min_val * (team_fgm - fgm)
        ast_pct = round(ast_pct_num / ast_pct_denom * 100, 1) if ast_pct_denom > 0 else 0.0
    else:
        ast_pct = 0.0

    # REB%
    if min_val > 0 and (team_reb + opp_reb) > 0:
        reb_pct_num = reb * (team_min / 5)
        reb_pct_denom = min_val * (team_reb + opp_reb)
        reb_pct = round(reb_pct_num / reb_pct_denom * 100, 1) if reb_pct_denom > 0 else 0.0
    else:
        reb_pct = 0.0

    # STL%
    if min_val > 0:
        stl_pct = round(stl * (team_min / 5) / min_val * 100, 1) if min_val > 0 else 0.0
    else:
        stl_pct = 0.0

    # BLK%
    if min_val > 0:
        blk_pct = round(blk * (team_min / 5) / min_val * 100, 1) if min_val > 0 else 0.0
    else:
        blk_pct = 0.0

    # TOV%
    tov_denom = fga + 0.44 * fta + tov
    tov_pct = round(tov / tov_denom * 100, 1) if tov_denom > 0 else 0.0

    return {
        "ts_pct": ts_pct, "efg_pct": efg_pct, "usg_pct": usg_pct,
        "ast_pct": ast_pct, "reb_pct": reb_pct, "stl_pct": stl_pct,
        "blk_pct": blk_pct, "tov_pct": tov_pct,
    }


def process_game_boxscore(boxscore: list, home_abbr: str, away_abbr: str) -> tuple:
    """处理单场 boxscore，返回 (球员数据列表, 球队数据)"""
    if not boxscore or len(boxscore) != 2:
        return [], {}

    # 根据 abbreviation 确定 home/away
    abbr_to_side = {}
    for team_data in boxscore:
        abbr = team_data.get("team_abbr", "")
        if abbr == home_abbr:
            abbr_to_side[abbr] = "home"
        elif abbr == away_abbr:
            abbr_to_side[abbr] = "away"
        else:
            # ESPN 缩写修正
            fixed = ESPN_ABBR_FIX.get(abbr, abbr)
            if fixed == home_abbr:
                abbr_to_side[abbr] = "home"
            elif fixed == away_abbr:
                abbr_to_side[abbr] = "away"

    all_players = []
    team_totals = {}

    for team_data in boxscore:
        abbr = team_data.get("team_abbr", "")
        side = abbr_to_side.get(abbr, "away")
        players = team_data.get("players", [])
        if not players:
            continue

        # 汇总球队数据
        t_fgm = t_fga = t_fg3m = t_fg3a = t_ftm = t_fta = 0
        t_pts = t_reb = t_oreb = t_dreb = t_ast = t_stl = t_blk = t_tov = t_pf = t_min = 0
        t_players_count = 0

        parsed = []
        for p in players:
            s = p["stats"]
            fg_m, fg_a, _ = parse_fg(s.get("FG"))
            tfg_m, tfg_a, _ = parse_fg(s.get("3PT"))
            ft_m, ft_a, _ = parse_fg(s.get("FT"))
            min_val = parse_stat(s.get("MIN"))
            pts = parse_stat(s.get("PTS"))
            reb = parse_stat(s.get("REB"))
            oreb = parse_stat(s.get("OREB"))
            dreb = parse_stat(s.get("DREB"))
            ast = parse_stat(s.get("AST"))
            stl = parse_stat(s.get("STL"))
            blk = parse_stat(s.get("BLK"))
            tov = parse_stat(s.get("TO"))
            pf = parse_stat(s.get("PF"))

            parsed.append({
                "espn_id": p["espn_id"], "name": p["name"],
                "team_abbr": p["team_abbr"], "side": side,
                "min": min_val, "pts": pts, "reb": reb, "oreb": oreb, "dreb": dreb,
                "ast": ast, "stl": stl, "blk": blk, "tov": tov, "pf": pf,
                "fgm": fg_m, "fga": fg_a, "fg3m": tfg_m, "fg3a": tfg_a,
                "ftm": ft_m, "fta": ft_a,
            })

            if min_val > 0:
                t_fgm += fg_m; t_fga += fg_a; t_fg3m += tfg_m; t_fg3a += tfg_a
                t_ftm += ft_m; t_fta += ft_a
                t_pts += pts; t_reb += reb; t_oreb += oreb; t_dreb += dreb
                t_ast += ast; t_stl += stl; t_blk += blk; t_tov += tov; t_pf += pf
                t_min += min_val
                t_players_count += 1

        # 对手篮板 = 另一队的总篮板
        opp_side = "away" if side == "home" else "home"
        opp_team = next((t for t in boxscore if abbr_to_side.get(t["team_abbr"]) == opp_side), None)
        opp_players = opp_team["players"] if opp_team else []
        opp_reb = sum(parse_stat(p["stats"].get("REB")) for p in opp_players if parse_stat(p["stats"].get("MIN")) > 0)

        # 计算每个球员的高阶指标
        for p in parsed:
            adv = compute_player_advanced(
                p["pts"], p["fgm"], p["fga"], p["fg3m"], p["fg3a"],
                p["ftm"], p["fta"], p["reb"], p["oreb"], p["dreb"],
                p["ast"], p["stl"], p["blk"], p["tov"], p["pf"], p["min"],
                t_fga, t_fta, t_tov, t_oreb, t_fgm, t_reb, opp_reb, t_min,
            )
            p.update(adv)
            all_players.append(p)

        # 球队数据
        team_totals[side] = {
            "fgm": t_fgm, "fga": t_fga, "fg3m": t_fg3m, "fg3a": t_fg3a,
            "ftm": t_ftm, "fta": t_fta, "pts": t_pts, "reb": t_reb,
            "oreb": t_oreb, "dreb": t_dreb, "ast": t_ast, "stl": t_stl,
            "blk": t_blk, "tov": t_tov, "pf": t_pf, "min": t_min,
            "players_count": t_players_count,
        }

    # 计算球队级高阶指标
    for side in ["home", "away"]:
        t = team_totals.get(side, {})
        if not t or t.get("fga", 0) == 0:
            continue

        # 回合数估算: Poss ≈ FGA + 0.44*FTA + TOV - OREB
        poss = t["fga"] + 0.44 * t["fta"] + t["tov"] - t["oreb"]
        t["possessions"] = round(poss, 1)

        # OffRtg = PTS / Poss * 100
        t["off_rtg"] = round(t["pts"] / poss * 100, 1) if poss > 0 else 0.0

        # TS%
        ts_denom = 2 * (t["fga"] + 0.44 * t["fta"])
        t["ts_pct"] = round(t["pts"] / ts_denom, 3) if ts_denom > 0 else 0.0

        # eFG%
        t["efg_pct"] = round((t["fgm"] + 0.5 * t["fg3m"]) / t["fga"], 3) if t["fga"] > 0 else 0.0

        # AST% = AST / FGM
        t["ast_pct"] = round(t["ast"] / t["fgm"] * 100, 1) if t["fgm"] > 0 else 0.0

        # REB% = TRB / (TRB + OppTRB)
        opp_side = "away" if side == "home" else "home"
        opp_t = team_totals.get(opp_side, {})
        opp_reb_total = opp_t.get("reb", 0)
        t["reb_pct"] = round(t["reb"] / (t["reb"] + opp_reb_total) * 100, 1) if (t["reb"] + opp_reb_total) > 0 else 0.0

    return all_players, team_totals


def aggregate_player_season_stats(all_player_games: dict) -> dict:
    """聚合球员逐场数据为赛季统计"""
    result = {}
    for espn_id, games in all_player_games.items():
        for season, season_games in games.items():
            if not season_games:
                continue

            gp = len(season_games)
            def avg(key):
                vals = [g.get(key, 0) for g in season_games if g.get("min", 0) > 0]
                return round(sum(vals) / len(vals), 1) if vals else 0.0

            def avg_all(key):
                vals = [g.get(key, 0) for g in season_games]
                return round(sum(vals) / len(vals), 1) if vals else 0.0

            def avg_pct(key):
                vals = [g.get(key, 0) for g in season_games if g.get("min", 0) > 0]
                return round(sum(vals) / len(vals), 3) if vals else 0.0

            mpg = avg_all("min")
            if mpg < 3.0:  # 跳出场时间太短的球员
                continue

            # 标准差
            pts_list = [g.get("pts", 0) for g in season_games if g.get("min", 0) > 0]
            if len(pts_list) > 1:
                pts_mean = sum(pts_list) / len(pts_list)
                pts_std = round((sum((x - pts_mean) ** 2 for x in pts_list) / (len(pts_list) - 1)) ** 0.5, 1)
                pts_cv = round(pts_std / max(pts_mean, 1), 3)
            else:
                pts_std = 0.0
                pts_cv = 0.0

            result[(espn_id, season)] = {
                "games_played": gp,
                "minutes_per_game": mpg,
                "points_per_game": avg_all("pts"),
                "rebounds_per_game": avg_all("reb"),
                "assists_per_game": avg_all("ast"),
                "steals_per_game": avg_all("stl"),
                "blocks_per_game": avg_all("blk"),
                "turnovers_per_game": avg_all("tov"),
                "fg_made_per_game": avg_all("fgm"),
                "fg_attempted_per_game": avg_all("fga"),
                "fg_percentage": round(avg_all("fgm") / max(avg_all("fga"), 1), 3),
                "three_made_per_game": avg_all("fg3m"),
                "three_attempted_per_game": avg_all("fg3a"),
                "three_percentage": round(avg_all("fg3m") / max(avg_all("fg3a"), 1), 3),
                "ft_made_per_game": avg_all("ftm"),
                "ft_attempted_per_game": avg_all("fta"),
                "ft_percentage": round(avg_all("ftm") / max(avg_all("fta"), 1), 3),
                "true_shooting_pct": avg_pct("ts_pct"),
                "effective_fg_pct": avg_pct("efg_pct"),
                "usage_rate": avg("usg_pct"),
                "assist_pct": avg("ast_pct"),
                "rebound_pct": avg("reb_pct"),
                "steal_pct": avg("stl_pct"),
                "block_pct": avg("blk_pct"),
                "turnover_pct": avg("tov_pct"),
                "points_std": pts_std,
                "points_cv": pts_cv,
            }

    return result


def run():
    logger.info("=" * 60)
    logger.info("ESPN 完整数据爬取 + 高阶数据计算")
    logger.info("=" * 60)

    # 获取映射
    abbr_map, id_to_abbr = get_team_abbr_map()
    espn_player_map = get_espn_player_map()
    logger.info(f"球队映射: {len(abbr_map)} 支")
    logger.info(f"球员映射: {len(espn_player_map)} 名")

    # 获取所有比赛记录
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED"
        ).order_by(GameRecord.game_date).all()

    logger.info(f"共 {len(games)} 场比赛需要处理")

    # 预加载所有比赛的主客场信息 (用于拆分)
    game_home_map = {}  # (team_id, game_date) -> is_home
    with SessionLocal() as db:
        all_records = db.query(GameRecord).filter(GameRecord.status == "FINISHED").all()
        for r in all_records:
            game_home_map[(r.home_team_id, r.game_date)] = True
            game_home_map[(r.away_team_id, r.game_date)] = False
    logger.info(f"预加载主客场映射: {len(game_home_map)} 条")

    # 缓存文件
    boxscore_cache_file = CACHE_DIR / "boxscore_cache.json"
    if boxscore_cache_file.exists():
        with open(boxscore_cache_file, "r", encoding="utf-8") as f:
            boxscore_cache = json.load(f)
    else:
        boxscore_cache = {}
    logger.info(f"缓存已有 {len(boxscore_cache)} 场比赛")

    # 球员逐场数据聚合
    # key: espn_id -> season -> [逐场数据列表]
    player_games = defaultdict(lambda: defaultdict(list))
    # 球队逐场数据聚合
    # key: (team_id, season) -> [逐场数据列表]
    team_games = defaultdict(list)

    # 处理每场比赛
    processed = 0
    skipped = 0
    failed = 0
    start_time = time.time()

    for i, game in enumerate(games):
        espn_id = str(game.nba_game_id).replace("espn_", "")

        # 检查缓存
        if espn_id in boxscore_cache:
            boxscore = boxscore_cache[espn_id]
            skipped += 1
        else:
            time.sleep(REQUEST_DELAY)
            boxscore = fetch_boxscore_for_game(espn_id)
            if boxscore:
                boxscore_cache[espn_id] = boxscore
                processed += 1
            else:
                failed += 1
                continue

        # 处理 boxscore (通过 GameRecord 确定主客场)
        home_abbr = id_to_abbr.get(game.home_team_id, "")
        away_abbr = id_to_abbr.get(game.away_team_id, "")
        all_players, team_totals = process_game_boxscore(boxscore, home_abbr, away_abbr)

        # 聚合球员数据
        for p in all_players:
            espn_pid = p["espn_id"]
            player_games[espn_pid][game.season].append(p)

        # 聚合球队数据
        for side in ["home", "away"]:
            team_id = game.home_team_id if side == "home" else game.away_team_id
            t = team_totals.get(side, {})
            if t:
                team_games[(team_id, game.season)].append({
                    "game_date": game.game_date,
                    "pts": t.get("pts", 0),
                    "opp_pts": team_totals.get("away" if side == "home" else "home", {}).get("pts", 0),
                    "fgm": t.get("fgm", 0), "fga": t.get("fga", 0),
                    "fg3m": t.get("fg3m", 0), "fg3a": t.get("fg3a", 0),
                    "ftm": t.get("ftm", 0), "fta": t.get("fta", 0),
                    "reb": t.get("reb", 0), "oreb": t.get("oreb", 0),
                    "ast": t.get("ast", 0), "stl": t.get("stl", 0),
                    "blk": t.get("blk", 0), "tov": t.get("tov", 0),
                    "possessions": t.get("possessions", 0),
                    "off_rtg": t.get("off_rtg", 0),
                    "ts_pct": t.get("ts_pct", 0),
                    "efg_pct": t.get("efg_pct", 0),
                    "ast_pct": t.get("ast_pct", 0),
                    "reb_pct": t.get("reb_pct", 0),
                })

        # 进度报告 (每 50 场)
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed
            remaining = (len(games) - i - 1) / max(speed, 0.01)
            logger.info(f"  进度: {i+1}/{len(games)}, "
                        f"新爬取 {processed}, 缓存跳过 {skipped}, 失败 {failed}, "
                        f"速度 {speed:.1f}/s, 剩余约 {remaining/60:.0f} 分钟")

        # 每 500 场保存一次缓存
        if (i + 1) % 500 == 0:
            with open(boxscore_cache_file, "w", encoding="utf-8") as f:
                json.dump(boxscore_cache, f)

    # 保存最终缓存
    with open(boxscore_cache_file, "w", encoding="utf-8") as f:
        json.dump(boxscore_cache, f)

    logger.info(f"\n爬取完成: 新爬取 {processed}, 缓存跳过 {skipped}, 失败 {failed}")

    # 聚合球员赛季数据
    logger.info("聚合球员赛季数据...")
    player_season_stats = aggregate_player_season_stats(player_games)
    logger.info(f"聚合完成: {len(player_season_stats)} 条球员赛季数据")

    # 写入数据库
    logger.info("写入数据库...")

    with SessionLocal() as db:
        # 清除旧的球员数据
        old_pd = db.query(PlayerData).count()
        if old_pd > 0:
            db.query(PlayerData).delete()
            db.commit()
            logger.info(f"  清除旧 PlayerData: {old_pd} 条")

        # 写入球员赛季数据
        added_pd = 0
        skipped_pd = 0
        for (espn_id, season), stats in player_season_stats.items():
            player = espn_player_map.get(espn_id)
            if not player:
                skipped_pd += 1
                continue

            pd = PlayerData(
                player_id=player.player_id,
                season=season,
                team_id=player.team_id,
                games_played=stats["games_played"],
                games_started=0,
                minutes_per_game=stats["minutes_per_game"],
                points_per_game=stats["points_per_game"],
                rebounds_per_game=stats["rebounds_per_game"],
                assists_per_game=stats["assists_per_game"],
                steals_per_game=stats["steals_per_game"],
                blocks_per_game=stats["blocks_per_game"],
                turnovers_per_game=stats["turnovers_per_game"],
                fg_made_per_game=stats["fg_made_per_game"],
                fg_attempted_per_game=stats["fg_attempted_per_game"],
                fg_percentage=stats["fg_percentage"],
                three_made_per_game=stats["three_made_per_game"],
                three_attempted_per_game=stats["three_attempted_per_game"],
                three_percentage=stats["three_percentage"],
                ft_made_per_game=stats["ft_made_per_game"],
                ft_attempted_per_game=stats["ft_attempted_per_game"],
                ft_percentage=stats["ft_percentage"],
                true_shooting_pct=stats["true_shooting_pct"],
                effective_fg_pct=stats["effective_fg_pct"],
                usage_rate=stats["usage_rate"],
                assist_pct=stats["assist_pct"],
                rebound_pct=stats["rebound_pct"],
                steal_pct=stats["steal_pct"],
                block_pct=stats["block_pct"],
                turnover_pct=stats["turnover_pct"],
                points_std=stats["points_std"],
                points_cv=stats["points_cv"],
                per=0, win_shares=0, bpm=0, vorp=0,
                isolation_pct=0, pick_roll_pct=0, spot_up_pct=0, post_up_pct=0,
                offensive_rating=0, defensive_rating=0, net_rating=0,
            )
            db.add(pd)
            added_pd += 1

        db.commit()
        logger.info(f"  写入 PlayerData: {added_pd}, 跳过(无匹配): {skipped_pd}")

        # 写入球队赛季数据
        old_td = db.query(TeamData).count()
        if old_td > 0:
            db.query(TeamData).delete()
            db.commit()
            logger.info(f"  清除旧 TeamData: {old_td} 条")

        added_td = 0
        for (team_id, season), games_list in team_games.items():
            if not games_list:
                continue

            gp = len(games_list)
            wins = sum(1 for g in games_list if g["pts"] > g["opp_pts"])
            losses = gp - wins

            def team_avg(key):
                vals = [g.get(key, 0) for g in games_list]
                return round(sum(vals) / len(vals), 1) if vals else 0.0

            def team_avg_pct(key):
                vals = [g.get(key, 0) for g in games_list]
                return round(sum(vals) / len(vals), 3) if vals else 0.0

            ppg = team_avg("pts")
            oppg = team_avg("opp_pts")

            # 主客场拆分 (使用预加载的映射)
            home_pf = [g["pts"] for g in games_list if game_home_map.get((team_id, g["game_date"]), False)]
            away_pf = [g["pts"] for g in games_list if not game_home_map.get((team_id, g["game_date"]), True)]
            home_wins = sum(1 for g in games_list if game_home_map.get((team_id, g["game_date"]), False) and g["pts"] > g["opp_pts"])
            home_losses_count = sum(1 for g in games_list if game_home_map.get((team_id, g["game_date"]), False) and g["pts"] <= g["opp_pts"])
            away_wins = sum(1 for g in games_list if not game_home_map.get((team_id, g["game_date"]), True) and g["pts"] > g["opp_pts"])
            away_losses_count = sum(1 for g in games_list if not game_home_map.get((team_id, g["game_date"]), True) and g["pts"] <= g["opp_pts"])

            # 近 10 场
            sorted_games = sorted(games_list, key=lambda x: x["game_date"])
            recent_10 = sorted_games[-10:]
            recent_wr = sum(1 for g in recent_10 if g["pts"] > g["opp_pts"]) / max(len(recent_10), 1)
            momentum = sum(g["pts"] for g in recent_10) / max(len(recent_10), 1)

            # 标准差
            pts_list = [g["pts"] for g in games_list]
            if len(pts_list) > 1:
                pts_mean = sum(pts_list) / len(pts_list)
                pts_std = round((sum((x - pts_mean) ** 2 for x in pts_list) / (len(pts_list) - 1)) ** 0.5, 1)
            else:
                pts_std = round(ppg * 0.12, 1)

            # 回合数 (取平均)
            avg_poss = team_avg("possessions")
            if avg_poss == 0:
                avg_poss = 100.0

            # 投篮命中率 (总命中/总出手)
            total_fgm = sum(g.get("fgm", 0) for g in games_list)
            total_fga = sum(g.get("fga", 0) for g in games_list)
            total_fg3m = sum(g.get("fg3m", 0) for g in games_list)
            total_fg3a = sum(g.get("fg3a", 0) for g in games_list)
            total_ftm = sum(g.get("ftm", 0) for g in games_list)
            total_fta = sum(g.get("fta", 0) for g in games_list)

            td = TeamData(
                team_id=team_id,
                season=season,
                wins=wins,
                losses=losses,
                win_percentage=round(wins / gp, 3) if gp > 0 else 0.5,
                home_wins=home_wins,
                home_losses=home_losses_count,
                away_wins=away_wins,
                away_losses=away_losses_count,
                points_per_game=ppg,
                assists_per_game=team_avg("ast"),
                rebounds_per_game=team_avg("reb"),
                offensive_rebounds=team_avg("oreb"),
                turnovers_per_game=team_avg("tov"),
                fg_percentage=round(total_fgm / total_fga, 3) if total_fga > 0 else 0,
                three_percentage=round(total_fg3m / total_fg3a, 3) if total_fg3a > 0 else 0,
                ft_percentage=round(total_ftm / total_fta, 3) if total_fta > 0 else 0,
                steals_per_game=team_avg("stl"),
                blocks_per_game=team_avg("blk"),
                opponent_points=oppg,
                pace=round(avg_poss, 1),
                offensive_rating=round(ppg / avg_poss * 100, 1) if avg_poss > 0 else 110.0,
                defensive_rating=round(oppg / avg_poss * 100, 1) if avg_poss > 0 else 110.0,
                points_std=pts_std,
                points_cv=round(pts_std / max(ppg, 1), 3),
                recent_win_rate=round(recent_wr, 3),
                momentum=round(momentum, 1),
                home_ppg=round(sum(home_pf) / len(home_pf), 1) if home_pf else ppg,
                away_ppg=round(sum(away_pf) / len(away_pf), 1) if away_pf else ppg,
                net_rating=round((ppg - oppg) / avg_poss * 100, 1) if avg_poss > 0 else 0,
                assist_pct=team_avg("ast_pct"),
                rebound_pct=team_avg("reb_pct"),
                effective_fg_pct=team_avg("efg_pct"),
                true_shooting_pct=team_avg("ts_pct"),
            )
            db.add(td)
            added_td += 1

        db.commit()
        logger.info(f"  写入 TeamData: {added_td}")

    logger.info("\n" + "=" * 60)
    logger.info("数据爬取 + 高阶计算完成")
    logger.info(f"  PlayerData: {added_pd} 条")
    logger.info(f"  TeamData: {added_td} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
