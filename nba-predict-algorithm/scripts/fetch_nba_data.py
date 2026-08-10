"""
使用 nba_api 从 stats.nba.com 采集真实 NBA 数据
替代原有的 ESPN API + NBA Stats API 直接调用
覆盖 2022-23 到 2025-26 四个赛季
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import Player, PlayerData, Team, TeamData, GameRecord

# nba_api 导入
from nba_api.stats.endpoints import (
    leaguedashplayerstats,
    leaguedashteamstats,
    leaguegamefinder,
    commonallplayers,
)

try:
    from nba_api.stats.endpoints import synergyplaytypes
    HAS_SYNERGY = True
except ImportError:
    HAS_SYNERGY = False
from nba_api.stats.static import teams as nba_teams_static
from nba_api.stats.static import players as nba_players_static

# 赛季列表
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]

# nba_api 请求间隔（秒）
REQUEST_DELAY = 0.6

# 内部 team_id -> nba_api team_id 映射
NBA_TEAM_ID_MAP = {
    1: 1610612737,   # ATL
    2: 1610612738,   # BOS
    3: 1610612751,   # BKN
    4: 1610612766,   # CHA
    5: 1610612741,   # CHI
    6: 1610612739,   # CLE
    7: 1610612765,   # DET
    8: 1610612754,   # IND
    9: 1610612748,   # MIA
    10: 1610612749,  # MIL
    11: 1610612752,  # NYK
    12: 1610612753,  # ORL
    13: 1610612755,  # PHI
    14: 1610612761,  # TOR
    15: 1610612764,  # WAS
    16: 1610612742,  # DAL
    17: 1610612743,  # DEN
    18: 1610612744,  # GSW
    19: 1610612745,  # HOU
    20: 1610612746,  # LAC
    21: 1610612747,  # LAL
    22: 1610612763,  # MEM
    23: 1610612750,  # MIN
    24: 1610612740,  # NOP
    25: 1610612760,  # OKC
    26: 1610612756,  # PHX
    27: 1610612757,  # POR
    28: 1610612758,  # SAC
    29: 1610612759,  # SAS
    30: 1610612762,  # UTA
}

# 反向映射: nba_api team_id -> 内部 team_id
NBA_TO_INTERNAL = {v: k for k, v in NBA_TEAM_ID_MAP.items()}


def _delay():
    """请求间隔"""
    time.sleep(REQUEST_DELAY)


def _safe_call(func, retries=3, **kwargs):
    """安全调用 nba_api，失败重试"""
    for attempt in range(retries):
        try:
            _delay()
            return func(**kwargs)
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"  请求失败 (attempt {attempt+1}): {e}，等待 {wait}s 重试")
                time.sleep(wait)
            else:
                logger.error(f"  请求最终失败: {e}")
                return None


def fetch_teams():
    """确保 30 支球队在数据库中"""
    logger.info("检查球队数据...")
    nba_teams = nba_teams_static.get_teams()

    with SessionLocal() as db:
        existing = {t.nba_id: t for t in db.query(Team).all()}
        added = 0

        for internal_id, nba_id in NBA_TEAM_ID_MAP.items():
            nba_id_str = str(nba_id)
            if nba_id_str in existing:
                continue

            # 找到对应的 nba_api 球队信息
            team_info = next((t for t in nba_teams if t["id"] == nba_id), None)
            if not team_info:
                continue

            team = Team(
                nba_id=nba_id_str,
                team_name=team_info.get("full_name", ""),
                team_name_en=team_info.get("full_name", ""),
                abbreviation=team_info.get("abbreviation", ""),
                conference="",
                division="",
                city=team_info.get("city", ""),
                status=1,
            )
            db.add(team)
            added += 1

        db.commit()
        logger.info(f"  球队: 新增 {added}, 总计 {db.query(Team).count()}")


def fetch_players_for_season(season: str):
    """获取某赛季的球员列表"""
    logger.info(f"[{season}] 获取球员列表...")

    data = _safe_call(
        commonallplayers.CommonAllPlayers,
        season=season,
        is_only_current_season=0,
    )
    if not data:
        return []

    df = data.get_data_frames()[0]
    players = []
    for _, row in df.iterrows():
        nba_team_id = row.get("TEAM_ID", 0)
        internal_team_id = NBA_TO_INTERNAL.get(nba_team_id)
        players.append({
            "nba_id": str(int(row["PERSON_ID"])),
            "name": row["DISPLAY_FIRST_LAST"],
            "team_id": internal_team_id,
        })

    with SessionLocal() as db:
        existing_ids = {p.nba_id for p in db.query(Player.nba_id).all()}
        added = 0
        for p in players:
            if p["nba_id"] in existing_ids:
                continue
            player = Player(
                nba_id=p["nba_id"],
                player_name=p["name"],
                player_name_en=p["name"],
                team_id=p["team_id"],
                status=1,
            )
            db.add(player)
            added += 1
        db.commit()
        logger.info(f"  球员: 新增 {added}, 总计 {db.query(Player).count()}")

    return players


def fetch_player_stats(season: str, measure_type: str = "Base"):
    """获取球员赛季数据 (Base 或 Advanced)"""
    label = "基础" if measure_type == "Base" else "高阶"
    logger.info(f"[{season}] 获取球员{label}数据...")

    data = _safe_call(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        measure_type_detailed_defense=measure_type,
        per_mode_detailed="PerGame",
    )
    if not data:
        return []

    df = data.get_data_frames()[0]
    logger.info(f"  获取到 {len(df)} 名球员{label}数据")
    return df.to_dict("records")


def fetch_team_stats(season: str, measure_type: str = "Base"):
    """获取球队赛季数据 (Base 或 Advanced)"""
    label = "基础" if measure_type == "Base" else "高阶"
    logger.info(f"[{season}] 获取球队{label}数据...")

    data = _safe_call(
        leaguedashteamstats.LeagueDashTeamStats,
        season=season,
        measure_type_detailed_defense=measure_type,
        per_mode_detailed="PerGame",
    )
    if not data:
        return []

    df = data.get_data_frames()[0]
    logger.info(f"  获取到 {len(df)} 支球队{label}数据")
    return df.to_dict("records")


def fetch_game_records(season: str):
    """获取某赛季的比赛记录"""
    logger.info(f"[{season}] 获取比赛记录...")

    data = _safe_call(
        leaguegamefinder.LeagueGameFinder,
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Regular Season",
    )
    if not data:
        return []

    df = data.get_data_frames()[0]
    # 过滤 NBA 比赛
    df = df[df["SEASON_ID"].str.startswith("2")]

    # 去重 (每场比赛有两条记录: 主队和客队)
    games = []
    seen = set()
    for _, row in df.iterrows():
        game_id = row["GAME_ID"]
        if game_id in seen:
            continue
        seen.add(game_id)

        # 判断主客场
        matchup = str(row.get("MATCHUP", ""))
        is_home = " vs. " in matchup

        games.append({
            "nba_game_id": game_id,
            "team_id": row["TEAM_ID"],
            "is_home": is_home,
            "pts": int(row["PTS"]) if row["PTS"] else 0,
            "wl": row.get("WL", ""),
        })

    # 配对主客场
    game_map = {}
    for g in games:
        gid = g["nba_game_id"]
        if gid not in game_map:
            game_map[gid] = {}
        if g["is_home"]:
            game_map[gid]["home"] = g
        else:
            game_map[gid]["away"] = g

    # 构建完整比赛记录
    records = []
    for gid, sides in game_map.items():
        if "home" not in sides or "away" not in sides:
            continue

        home = sides["home"]
        away = sides["away"]
        home_tid = NBA_TO_INTERNAL.get(home["team_id"])
        away_tid = NBA_TO_INTERNAL.get(away["team_id"])

        if not home_tid or not away_tid:
            continue

        records.append({
            "nba_game_id": gid,
            "home_team_id": home_tid,
            "away_team_id": away_tid,
            "home_score": home["pts"],
            "away_score": away["pts"],
            "home_win": 1 if home["pts"] > away["pts"] else 0,
        })

    logger.info(f"  获取到 {len(records)} 场比赛")
    return records


def fetch_playoff_records(season: str):
    """获取季后赛比赛记录"""
    logger.info(f"[{season}] 获取季后赛记录...")

    data = _safe_call(
        leaguegamefinder.LeagueGameFinder,
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Playoffs",
    )
    if not data:
        return []

    df = data.get_data_frames()[0]
    df = df[df["SEASON_ID"].str.startswith("2")]

    games = []
    seen = set()
    for _, row in df.iterrows():
        game_id = row["GAME_ID"]
        if game_id in seen:
            continue
        seen.add(game_id)

        matchup = str(row.get("MATCHUP", ""))
        is_home = " vs. " in matchup

        games.append({
            "nba_game_id": game_id,
            "team_id": row["TEAM_ID"],
            "is_home": is_home,
            "pts": int(row["PTS"]) if row["PTS"] else 0,
        })

    game_map = {}
    for g in games:
        gid = g["nba_game_id"]
        if gid not in game_map:
            game_map[gid] = {}
        if g["is_home"]:
            game_map[gid]["home"] = g
        else:
            game_map[gid]["away"] = g

    records = []
    for gid, sides in game_map.items():
        if "home" not in sides or "away" not in sides:
            continue
        home = sides["home"]
        away = sides["away"]
        home_tid = NBA_TO_INTERNAL.get(home["team_id"])
        away_tid = NBA_TO_INTERNAL.get(away["team_id"])
        if not home_tid or not away_tid:
            continue
        records.append({
            "nba_game_id": gid,
            "home_team_id": home_tid,
            "away_team_id": away_tid,
            "home_score": home["pts"],
            "away_score": away["pts"],
            "home_win": 1 if home["pts"] > away["pts"] else 0,
        })

    logger.info(f"  获取到 {len(records)} 场季后赛")
    return records


def save_game_records(records: list, season: str, is_playoff: bool = False):
    """保存比赛记录到数据库"""
    with SessionLocal() as db:
        existing_ids = {
            r[0] for r in db.query(GameRecord.nba_game_id).filter(
                GameRecord.season == season
            ).all()
        }

        added = 0
        for r in records:
            if r["nba_game_id"] in existing_ids:
                continue

            gr = GameRecord(
                nba_game_id=r["nba_game_id"],
                season=season,
                game_date="2024-01-01",  # nba_api LeagueGameFinder 不直接给日期，后续从 boxscore 补
                game_type="Playoffs" if is_playoff else "Regular Season",
                home_team_id=r["home_team_id"],
                away_team_id=r["away_team_id"],
                home_score=r["home_score"],
                away_score=r["away_score"],
                home_win=r["home_win"],
                score_diff=r["home_score"] - r["away_score"],
                total_score=r["home_score"] + r["away_score"],
                is_playoff=1 if is_playoff else 0,
                status="FINISHED",
            )
            db.add(gr)
            added += 1

        db.commit()
        logger.info(f"  保存比赛记录: 新增 {added}")


def save_player_data(base_stats: list, adv_stats: list, season: str):
    """合并基础和高阶数据，写入 PlayerData"""
    logger.info(f"[{season}] 写入球员数据...")

    # 构建高阶数据映射 (PLAYER_ID -> stats)
    adv_map = {}
    for row in adv_stats:
        pid = str(int(row["PLAYER_ID"]))
        adv_map[pid] = row

    with SessionLocal() as db:
        # 清除该赛季旧数据
        deleted = db.query(PlayerData).filter(PlayerData.season == season).delete()
        if deleted:
            logger.info(f"  清除旧数据 {deleted} 条")

        # 构建 nba_id -> player 映射
        players = {p.nba_id: p for p in db.query(Player).all()}

        added = 0
        skipped = 0

        for row in base_stats:
            nba_id = str(int(row["PLAYER_ID"]))
            player = players.get(nba_id)
            if not player:
                skipped += 1
                continue

            internal_team_id = NBA_TO_INTERNAL.get(row.get("TEAM_ID", 0))
            gp = int(row.get("GP", 0) or 0)
            if gp == 0:
                continue

            # 基础数据
            mpg = float(row.get("MIN", 0) or 0)
            pts = float(row.get("PTS", 0) or 0)
            reb = float(row.get("REB", 0) or 0)
            ast = float(row.get("AST", 0) or 0)
            stl = float(row.get("STL", 0) or 0)
            blk = float(row.get("BLK", 0) or 0)
            tov = float(row.get("TOV", 0) or 0)
            fg_m = float(row.get("FGM", 0) or 0)
            fg_a = float(row.get("FGA", 0) or 0)
            fg_pct = float(row.get("FG_PCT", 0) or 0)
            tfg_m = float(row.get("FG3M", 0) or 0)
            tfg_a = float(row.get("FG3A", 0) or 0)
            tfg_pct = float(row.get("FG3_PCT", 0) or 0)
            ft_m = float(row.get("FTM", 0) or 0)
            ft_a = float(row.get("FTA", 0) or 0)
            ft_pct = float(row.get("FT_PCT", 0) or 0)
            gs = int(row.get("GS", 0) or 0)

            # 高阶数据
            adv = adv_map.get(nba_id, {})
            per = float(adv.get("PIE", 0) or 0) * 15  # PIE 近似 PER
            ts_pct = float(adv.get("TS_PCT", 0) or 0)
            usg = float(adv.get("USG_PCT", 0) or 0) * 100
            off_rtg = float(adv.get("OFF_RATING", 0) or 0)
            def_rtg = float(adv.get("DEF_RATING", 0) or 0)
            net_rtg = float(adv.get("NET_RATING", 0) or 0)
            ast_pct = float(adv.get("AST_PCT", 0) or 0) * 100
            reb_pct = float(adv.get("REB_PCT", 0) or 0) * 100
            stl_pct = float(adv.get("STL_PCT", 0) or 0) * 100
            blk_pct = float(adv.get("BLK_PCT", 0) or 0) * 100
            tov_pct = float(adv.get("TOV_PCT", 0) or 0) * 100
            efg_pct = float(adv.get("E_OFF_RATING", 0) or 0)
            if efg_pct == 0:
                efg_pct = float(adv.get("EFG_PCT", 0) or 0)

            # 打法分布 (PlayTypeStats, 可能失败)
            iso_pct = 0.0
            pr_pct = 0.0
            spot_pct = 0.0
            post_pct = 0.0

            pd = PlayerData(
                player_id=player.player_id,
                season=season,
                team_id=internal_team_id,
                games_played=gp,
                games_started=gs,
                minutes_per_game=round(mpg, 1),
                points_per_game=round(pts, 1),
                rebounds_per_game=round(reb, 1),
                assists_per_game=round(ast, 1),
                steals_per_game=round(stl, 1),
                blocks_per_game=round(blk, 1),
                turnovers_per_game=round(tov, 1),
                fg_made_per_game=round(fg_m, 1),
                fg_attempted_per_game=round(fg_a, 1),
                fg_percentage=round(fg_pct, 3),
                three_made_per_game=round(tfg_m, 1),
                three_attempted_per_game=round(tfg_a, 1),
                three_percentage=round(tfg_pct, 3),
                ft_made_per_game=round(ft_m, 1),
                ft_attempted_per_game=round(ft_a, 1),
                ft_percentage=round(ft_pct, 3),
                per=round(per, 1),
                true_shooting_pct=round(ts_pct, 3),
                usage_rate=round(usg, 1),
                win_shares=0,
                bpm=0,
                vorp=0,
                isolation_pct=round(iso_pct, 3),
                pick_roll_pct=round(pr_pct, 3),
                spot_up_pct=round(spot_pct, 3),
                post_up_pct=round(post_pct, 3),
                points_std=0,  # 后续从逐场数据计算
                points_cv=0,
                offensive_rating=round(off_rtg, 1),
                defensive_rating=round(def_rtg, 1),
                net_rating=round(net_rtg, 1),
                assist_pct=round(ast_pct, 1),
                rebound_pct=round(reb_pct, 1),
                steal_pct=round(stl_pct, 1),
                block_pct=round(blk_pct, 1),
                turnover_pct=round(tov_pct, 1),
                effective_fg_pct=round(efg_pct, 3),
            )
            db.add(pd)
            added += 1

        db.commit()
        logger.info(f"  写入 PlayerData: {added}, 跳过: {skipped}")


def save_team_data(base_stats: list, adv_stats: list, season: str):
    """合并基础和高阶数据，写入 TeamData"""
    logger.info(f"[{season}] 写入球队数据...")

    adv_map = {}
    for row in adv_stats:
        tid = row.get("TEAM_ID", 0)
        adv_map[tid] = row

    with SessionLocal() as db:
        deleted = db.query(TeamData).filter(TeamData.season == season).delete()
        if deleted:
            logger.info(f"  清除旧数据 {deleted} 条")

        added = 0
        for row in base_stats:
            nba_team_id = row.get("TEAM_ID", 0)
            internal_id = NBA_TO_INTERNAL.get(nba_team_id)
            if not internal_id:
                continue

            gp = int(row.get("GP", 0) or 0)
            if gp == 0:
                continue

            wins = int(row.get("W", 0) or 0)
            losses = int(row.get("L", 0) or 0)
            win_pct = float(row.get("W_PCT", 0) or 0)
            pts = float(row.get("PTS", 0) or 0)
            reb = float(row.get("REB", 0) or 0)
            ast = float(row.get("AST", 0) or 0)
            tov = float(row.get("TOV", 0) or 0)
            stl = float(row.get("STL", 0) or 0)
            blk = float(row.get("BLK", 0) or 0)
            fg_pct = float(row.get("FG_PCT", 0) or 0)
            tfg_pct = float(row.get("FG3_PCT", 0) or 0)
            ft_pct = float(row.get("FT_PCT", 0) or 0)
            opp_pts = float(row.get("OPP_PTS", 0) or 0)
            opp_fg_pct = float(row.get("OPP_FG_PCT", 0) or 0)
            opp_tfg_pct = float(row.get("OPP_FG3_PCT", 0) or 0)

            # 高阶数据
            adv = adv_map.get(nba_team_id, {})
            pace = float(adv.get("PACE", 0) or 0)
            off_rtg = float(adv.get("OFF_RATING", 0) or 0)
            def_rtg = float(adv.get("DEF_RATING", 0) or 0)
            net_rtg = float(adv.get("NET_RATING", 0) or 0)
            ast_pct = float(adv.get("AST_PCT", 0) or 0) * 100
            reb_pct = float(adv.get("REB_PCT", 0) or 0) * 100
            efg_pct = float(adv.get("EFG_PCT", 0) or 0)
            ts_pct = float(adv.get("TS_PCT", 0) or 0)
            oreb = float(adv.get("OREB", 0) or 0)

            td = TeamData(
                team_id=internal_id,
                season=season,
                wins=wins,
                losses=losses,
                win_percentage=round(win_pct, 3),
                points_per_game=round(pts, 1),
                assists_per_game=round(ast, 1),
                rebounds_per_game=round(reb, 1),
                turnovers_per_game=round(tov, 1),
                fg_percentage=round(fg_pct, 3),
                three_percentage=round(tfg_pct, 3),
                ft_percentage=round(ft_pct, 3),
                steals_per_game=round(stl, 1),
                blocks_per_game=round(blk, 1),
                opponent_points=round(opp_pts, 1),
                opponent_fg_percentage=round(opp_fg_pct, 3),
                opponent_three_pct=round(opp_tfg_pct, 3),
                pace=round(pace, 1),
                offensive_rating=round(off_rtg, 1),
                defensive_rating=round(def_rtg, 1),
                offensive_rebounds=round(oreb, 1),
                # 衍生数据后续 compute_team_stats 填充
                home_wins=0,
                home_losses=0,
                away_wins=0,
                away_losses=0,
                points_std=0,
                points_cv=0,
                recent_win_rate=0,
                momentum=0,
                home_ppg=0,
                away_ppg=0,
                # 新增高阶列
                net_rating=round(net_rtg, 1),
                assist_pct=round(ast_pct, 1),
                rebound_pct=round(reb_pct, 1),
                effective_fg_pct=round(efg_pct, 3),
                true_shooting_pct=round(ts_pct, 3),
            )
            db.add(td)
            added += 1

        db.commit()
        logger.info(f"  写入 TeamData: {added}")


def try_fetch_play_type_stats(season: str):
    """尝试获取打法分布数据 (可能失败)"""
    if not HAS_SYNERGY:
        logger.warning(f"[{season}] SynergyPlayTypes 不可用，使用默认值 0")
        return {}
    logger.info(f"[{season}] 尝试获取打法分布...")
    try:
        data = _safe_call(
            synergyplaytypes.SynergyPlayTypes,
            season=season,
            league_id="00",
            player_or_team_abbreviation="P",
            type_grouping_nullable="offensive",
        )
        if not data:
            logger.warning(f"  打法分布获取失败，使用默认值 0")
            return {}

        df = data.get_data_frames()[0]
        result = {}
        for _, row in df.iterrows():
            pid = str(int(row.get("PLAYER_ID", 0)))
            ptype = row.get("PLAY_TYPE", "")
            freq = float(row.get("POSS_PCT", 0) or 0)

            if pid not in result:
                result[pid] = {}
            result[pid][ptype] = freq

        logger.info(f"  获取到 {len(result)} 名球员打法分布")
        return result
    except Exception as e:
        logger.warning(f"  打法分布获取失败: {e}，使用默认值 0")
        return {}


def update_play_type_data(season: str):
    """更新打法分布数据到 PlayerData"""
    play_types = try_fetch_play_type_stats(season)
    if not play_types:
        return

    with SessionLocal() as db:
        pd_records = db.query(PlayerData).filter(PlayerData.season == season).all()
        nba_id_map = {p.player_id: p.nba_id for p in db.query(Player).all()}

        updated = 0
        for pd in pd_records:
            nba_id = nba_id_map.get(pd.player_id)
            if not nba_id or nba_id not in play_types:
                continue

            pt = play_types[nba_id]
            pd.isolation_pct = round(float(pt.get("Isolation", 0) or 0) * 100, 1)
            pd.pick_roll_pct = round(float(pt.get("Pick & Roll Ball Handler", 0) or 0) * 100, 1)
            pd.spot_up_pct = round(float(pt.get("Spot Up", 0) or 0) * 100, 1)
            pd.post_up_pct = round(float(pt.get("Post Up", 0) or 0) * 100, 1)
            updated += 1

        db.commit()
        logger.info(f"  更新打法分布: {updated} 名球员")


def run():
    logger.info("=" * 60)
    logger.info("nba_api 数据采集开始")
    logger.info("=" * 60)

    # Step 1: 确保球队数据
    fetch_teams()

    for season in SEASONS:
        logger.info(f"\n{'='*40}")
        logger.info(f"赛季: {season}")
        logger.info(f"{'='*40}")

        # Step 2: 球员列表
        fetch_players_for_season(season)

        # Step 3: 球员基础数据
        player_base = fetch_player_stats(season, "Base")

        # Step 4: 球员高阶数据
        player_adv = fetch_player_stats(season, "Advanced")

        # Step 5: 写入球员数据
        if player_base:
            save_player_data(player_base, player_adv, season)

        # Step 6: 尝试打法分布
        update_play_type_data(season)

        # Step 7: 球队基础数据
        team_base = fetch_team_stats(season, "Base")

        # Step 8: 球队高阶数据
        team_adv = fetch_team_stats(season, "Advanced")

        # Step 9: 写入球队数据
        if team_base:
            save_team_data(team_base, team_adv, season)

        # Step 10: 比赛记录 (常规赛)
        reg_games = fetch_game_records(season)
        if reg_games:
            save_game_records(reg_games, season, is_playoff=False)

        # Step 11: 比赛记录 (季后赛)
        playoff_games = fetch_playoff_records(season)
        if playoff_games:
            save_game_records(playoff_games, season, is_playoff=True)

    logger.info("\n" + "=" * 60)
    logger.info("nba_api 数据采集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
