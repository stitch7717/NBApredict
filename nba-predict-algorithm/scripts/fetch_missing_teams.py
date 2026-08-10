"""
补抓缺失球队的球员数据
从 boxscore 中按赛季分别统计，不依赖阵容表
自动从 boxscore 识别球员所属球队
"""
import sys
import json
import time
import urllib.request
import ssl
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.db.database import SessionLocal
from app.db.models import GameRecord, Player, PlayerData, Team

ctx = ssl.create_default_context()
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MIN_MINUTES = 3.0
TARGET_TEAMS = [11, 15, 18, 24, 29, 30]

ESPN_ABBR_FIX = {"GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS", "NY": "NYK", "SA": "SAS"}

# team_id -> ESPN abbr (用于 roster API)
ESPN_ABBR = {
    1: "ATL", 2: "BOS", 3: "BKN", 4: "CHA", 5: "CHI",
    6: "CLE", 7: "DET", 8: "IND", 9: "MIA", 10: "MIL",
    11: "NY", 12: "ORL", 13: "PHI", 14: "TOR", 15: "WSH",
    16: "DAL", 17: "DEN", 18: "GS", 19: "HOU", 20: "LAC",
    21: "LAL", 22: "MEM", 23: "MIN", 24: "NO", 25: "OKC",
    26: "PHX", 27: "POR", 28: "SAC", 29: "SA", 30: "UTAH",
}


def fetch_json(url, retries=3, base_delay=2.0):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            return json.loads(resp.read())
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.debug(f"请求失败: {url[:60]}... {e}")
    return {}


def parse_stat(val, default=0):
    if not val or val == "-" or val == "DNP":
        return default
    try:
        return float(val)
    except:
        return default


def get_abbr_map():
    with SessionLocal() as db:
        teams = db.query(Team).all()
        result = {t.abbreviation: t.team_id for t in teams}
        for espn_abbr, db_abbr in ESPN_ABBR_FIX.items():
            if db_abbr in result:
                result[espn_abbr] = result[db_abbr]
        return result


def new_stats():
    return {
        "games": 0, "team_id": None, "minutes": [], "points": [], "rebounds": [],
        "assists": [], "steals": [], "blocks": [], "turnovers": [],
        "fg_made": [], "fg_att": [], "three_made": [], "three_att": [],
        "ft_made": [], "ft_att": [],
    }


def ensure_player_in_db(db, espn_id, name, team_id, abbr_map):
    """确保球员在数据库中，返回 player 对象"""
    existing = db.query(Player).filter(Player.nba_id == espn_id).first()
    if existing:
        return existing

    player = Player(
        nba_id=espn_id,
        player_name=name,
        player_name_en=name,
        position="",
        jersey_number=None,
        team_id=team_id,
        age=None, height=0, weight=0,
        experience=None,
        all_star_count=0, all_star_last=0,
        injury_status="健康",
        player_type="普通球员",
        status=1,
    )
    db.add(player)
    db.flush()
    return player


def run():
    logger.info("补抓缺失球队球员数据（从 boxscore 自动识别）")
    abbr_map = get_abbr_map()

    # 按赛季找涉及目标球队的比赛
    with SessionLocal() as db:
        all_games = db.query(GameRecord).filter(
            GameRecord.status == "FINISHED",
            GameRecord.season.in_(["2024-25", "2025-26"]),
        ).all()

        season_dates = defaultdict(set)
        for g in all_games:
            if g.home_team_id in TARGET_TEAMS or g.away_team_id in TARGET_TEAMS:
                season_dates[g.season].add(g.game_date.strftime("%Y%m%d"))

    total_dates = sum(len(v) for v in season_dates.values())
    logger.info(f"需要抓取 {total_dates} 个日期")

    # 按赛季抓取 boxscore
    # season -> espn_pid -> stats
    player_stats = defaultdict(lambda: defaultdict(new_stats))
    player_teams = defaultdict(dict)  # season -> espn_pid -> team_id
    player_names = {}  # espn_pid -> name

    processed = 0
    for season, dates in season_dates.items():
        logger.info(f"赛季 {season}: {len(dates)} 个日期")
        for i, date_str in enumerate(sorted(dates)):
            url = f"{ESPN_SCOREBOARD}?dates={date_str}&limit=30"
            data = fetch_json(url)
            events = data.get("events", [])

            for e in events:
                comp = e.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue

                team_ids_in_game = []
                for c in competitors:
                    abbr = c.get("team", {}).get("abbreviation", "")
                    tid = abbr_map.get(abbr)
                    if tid:
                        team_ids_in_game.append(tid)

                if not any(tid in TARGET_TEAMS for tid in team_ids_in_game):
                    continue

                espn_id = str(e.get("id", ""))
                if not espn_id:
                    continue

                box_data = fetch_json(f"{ESPN_SUMMARY}?event={espn_id}")
                bs = box_data.get("boxscore", {})
                for team_data in bs.get("players", []):
                    team_abbr = team_data.get("team", {}).get("abbreviation", "")
                    team_tid = abbr_map.get(team_abbr)

                    for stat_group in team_data.get("statistics", []):
                        labels = stat_group.get("labels", [])
                        for ath_entry in stat_group.get("athletes", []):
                            ath = ath_entry.get("athlete", {})
                            pid = str(ath.get("id", ""))
                            name = ath.get("displayName", "")
                            stats = ath_entry.get("stats", [])
                            if not pid or not stats or len(stats) != len(labels):
                                continue

                            stat_map = dict(zip(labels, stats))
                            s = player_stats[season][pid]
                            s["games"] += 1
                            s["minutes"].append(parse_stat(stat_map.get("MIN")))
                            s["points"].append(parse_stat(stat_map.get("PTS")))
                            s["rebounds"].append(parse_stat(stat_map.get("REB")))
                            s["assists"].append(parse_stat(stat_map.get("AST")))
                            s["steals"].append(parse_stat(stat_map.get("STL")))
                            s["blocks"].append(parse_stat(stat_map.get("BLK")))
                            s["turnovers"].append(parse_stat(stat_map.get("TO")))

                            fg = str(stat_map.get("FG", "")).split("-")
                            s["fg_made"].append(int(fg[0]) if len(fg) == 2 and fg[0].isdigit() else 0)
                            s["fg_att"].append(int(fg[1]) if len(fg) == 2 and fg[1].isdigit() else 0)
                            t = str(stat_map.get("3PT", "")).split("-")
                            s["three_made"].append(int(t[0]) if len(t) == 2 and t[0].isdigit() else 0)
                            s["three_att"].append(int(t[1]) if len(t) == 2 and t[1].isdigit() else 0)
                            ft = str(stat_map.get("FT", "")).split("-")
                            s["ft_made"].append(int(ft[0]) if len(ft) == 2 and ft[0].isdigit() else 0)
                            s["ft_att"].append(int(ft[1]) if len(ft) == 2 and ft[1].isdigit() else 0)

                            if team_tid:
                                player_teams[season][pid] = team_tid
                            player_names[pid] = name

                time.sleep(0.3)

            processed += 1
            if (i + 1) % 10 == 0:
                logger.info(f"  进度: {i+1}/{len(dates)}, {processed} 场")

    logger.info(f"处理 {processed} 场比赛, {len(player_names)} 名球员")

    # 写入数据库
    with SessionLocal() as db:
        # 已有的 (player_id, season) 对
        existing_keys = set()
        for pd in db.query(PlayerData).all():
            existing_keys.add((pd.player_id, pd.season))

        def avg_all(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0

        added = 0
        for season, pid_stats in player_stats.items():
            for pid, s in pid_stats.items():
                gp = s["games"]
                mpg = avg_all(s["minutes"])
                if gp == 0 or mpg < MIN_MINUTES:
                    continue

                team_id = player_teams[season].get(pid)
                if not team_id:
                    continue

                # 确保球员在数据库中
                name = player_names.get(pid, f"Player_{pid}")
                player = ensure_player_in_db(db, pid, name, team_id, abbr_map)

                key = (player.player_id, season)
                if key in existing_keys:
                    continue

                ppg = avg_all(s["points"])
                fg_m = avg_all(s["fg_made"])
                fg_a = avg_all(s["fg_att"])
                three_m = avg_all(s["three_made"])
                three_a = avg_all(s["three_att"])
                ft_m = avg_all(s["ft_made"])
                ft_a = avg_all(s["ft_att"])
                ts_denom = 2 * (fg_a + 0.44 * ft_a)

                pd_record = PlayerData(
                    player_id=player.player_id, season=season, team_id=team_id,
                    games_played=gp, games_started=0, minutes_per_game=mpg,
                    points_per_game=ppg,
                    rebounds_per_game=avg_all(s["rebounds"]),
                    assists_per_game=avg_all(s["assists"]),
                    steals_per_game=avg_all(s["steals"]),
                    blocks_per_game=avg_all(s["blocks"]),
                    turnovers_per_game=avg_all(s["turnovers"]),
                    fg_made_per_game=fg_m, fg_attempted_per_game=fg_a,
                    fg_percentage=round(fg_m / fg_a, 3) if fg_a > 0 else 0,
                    three_made_per_game=three_m, three_attempted_per_game=three_a,
                    three_percentage=round(three_m / three_a, 3) if three_a > 0 else 0,
                    ft_made_per_game=ft_m, ft_attempted_per_game=ft_a,
                    ft_percentage=round(ft_m / ft_a, 3) if ft_a > 0 else 0,
                    per=0, true_shooting_pct=round(ppg / ts_denom, 3) if ts_denom > 0 else 0,
                    usage_rate=0, win_shares=0, bpm=0, vorp=0,
                    isolation_pct=0, pick_roll_pct=0, spot_up_pct=0, post_up_pct=0,
                    points_std=0, points_cv=0,
                )
                db.add(pd_record)
                existing_keys.add(key)
                added += 1

        db.commit()
        logger.info(f"补充数据: {added}")

        # 每队保留 top 12（2025-26），删除多余
        pdata = db.query(PlayerData).filter(PlayerData.season == "2025-26").all()
        team_players = defaultdict(list)
        for pd in pdata:
            team_players[pd.team_id].append(pd)

        keep_ids = set()
        for tid, plist in team_players.items():
            plist.sort(key=lambda x: (x.points_per_game or 0, x.minutes_per_game or 0), reverse=True)
            for p in plist[:12]:
                keep_ids.add(p.player_id)

        delete_count = 0
        for pd in pdata:
            if pd.player_id not in keep_ids:
                db.delete(pd)
                delete_count += 1

        # 删除无数据球员
        all_p = db.query(Player).all()
        has_data = set(pd.player_id for pd in db.query(PlayerData).all())
        del_player = 0
        for p in all_p:
            if p.player_id not in has_data:
                db.delete(p)
                del_player += 1

        db.commit()

        # 最终统计
        from collections import Counter
        final_pdata = db.query(PlayerData).filter(PlayerData.season == "2025-26").all()
        team_counts = Counter(pd.team_id for pd in final_pdata)
        logger.info(f"删除多余数据: {delete_count}")
        logger.info(f"删除无数据球员: {del_player}")
        logger.info(f"最终球员: {db.query(Player).count()}")
        logger.info(f"最终 PlayerData: {len(final_pdata)}")
        for tid in sorted(team_counts.keys()):
            logger.info(f"  球队 {tid}: {team_counts[tid]}")


if __name__ == "__main__":
    run()
