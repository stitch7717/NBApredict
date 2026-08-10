"""
数据查询接口 — 供前端使用
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import date, timedelta

from app.db.database import SessionLocal
from app.db.models import Team, TeamData, Player, PlayerData, GameRecord

router = APIRouter()


@router.get("/teams", summary="球队列表")
async def get_teams(season: str = "2025-26"):
    with SessionLocal() as db:
        teams = db.query(Team).filter(Team.status == 1).all()
        team_ids = [t.team_id for t in teams]
        team_data_list = db.query(TeamData).filter(
            TeamData.team_id.in_(team_ids),
            TeamData.season == season,
        ).all()
        team_data_map = {td.team_id: td for td in team_data_list}
        result = []
        for t in teams:
            td = team_data_map.get(t.team_id)
            result.append({
                "team_id": t.team_id,
                "team_name": t.team_name,
                "team_name_en": t.team_name_en,
                "abbreviation": t.abbreviation,
                "conference": t.conference,
                "division": t.division,
                "city": t.city,
                "arena": t.arena,
                "strength_level": t.strength_level,
                "strength_score": t.strength_score,
                "season_data": {
                    "wins": td.wins if td else 0,
                    "losses": td.losses if td else 0,
                    "win_percentage": td.win_percentage if td else 0,
                    "points_per_game": td.points_per_game if td else 0,
                    "opponent_points": td.opponent_points if td else 0,
                    "pace": td.pace if td else 0,
                    "offensive_rating": td.offensive_rating if td else 0,
                    "defensive_rating": td.defensive_rating if td else 0,
                    "net_rating": td.net_rating if td else 0,
                } if td else None,
            })
        return result


@router.get("/teams/{team_id}", summary="球队详情")
async def get_team(team_id: int, season: str = "2025-26"):
    with SessionLocal() as db:
        t = db.query(Team).filter(Team.team_id == team_id).first()
        if not t:
            return {"error": "Team not found"}

        td = db.query(TeamData).filter(
            TeamData.team_id == team_id,
            TeamData.season == season,
        ).first()

        # 获取所有赛季数据
        all_seasons = db.query(TeamData).filter(TeamData.team_id == team_id).all()

        return {
            "team_id": t.team_id,
            "team_name": t.team_name,
            "team_name_en": t.team_name_en,
            "abbreviation": t.abbreviation,
            "conference": t.conference,
            "division": t.division,
            "city": t.city,
            "arena": t.arena,
            "offense_type": t.offense_type,
            "defense_type": t.defense_type,
            "strength_level": t.strength_level,
            "strength_score": t.strength_score,
            "season_data": _team_data_dict(td) if td else None,
            "seasons": [_team_data_dict(s) for s in all_seasons],
        }


@router.get("/teams/{team_id}/roster", summary="球队阵容")
async def get_team_roster(team_id: int, season: str = "2025-26"):
    with SessionLocal() as db:
        players = db.query(Player).filter(
            Player.team_id == team_id,
            Player.status == 1,
        ).all()

        player_ids = [p.player_id for p in players]
        player_data_list = db.query(PlayerData).filter(
            PlayerData.player_id.in_(player_ids),
            PlayerData.season == season,
        ).all() if player_ids else []
        player_data_map = {pd.player_id: pd for pd in player_data_list}

        result = []
        for p in players:
            pd = player_data_map.get(p.player_id)
            result.append({
                "player_id": p.player_id,
                "player_name": p.player_name,
                "player_name_en": p.player_name_en,
                "position": p.position,
                "jersey_number": p.jersey_number,
                "age": p.age,
                "height": p.height,
                "weight": p.weight,
                "player_role": p.player_role,
                "impact_score": p.impact_score,
                "injury_status": p.injury_status,
                "season_data": _player_data_dict(pd) if pd else None,
            })
        return result


@router.get("/players", summary="球员列表")
async def get_players(
    season: str = "2025-26",
    sort_by: str = "points_per_game",
    order: str = "desc",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    with SessionLocal() as db:
        query = db.query(Player, PlayerData).join(
            PlayerData, Player.player_id == PlayerData.player_id
        ).filter(
            PlayerData.season == season,
            Player.status == 1,
        )

        # 排序
        sort_col = getattr(PlayerData, sort_by, PlayerData.points_per_game)
        if order == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        total = query.count()
        items = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": [
                {
                    "player_id": p.player_id,
                    "player_name": p.player_name,
                    "player_name_en": p.player_name_en,
                    "position": p.position,
                    "jersey_number": p.jersey_number,
                    "team_id": p.team_id,
                    "age": p.age,
                    "player_role": p.player_role,
                    "impact_score": p.impact_score,
                    **_player_data_dict(pd),
                }
                for p, pd in items
            ],
        }


@router.get("/players/{player_id}", summary="球员详情")
async def get_player(player_id: int, season: str = "2025-26"):
    with SessionLocal() as db:
        p = db.query(Player).filter(Player.player_id == player_id).first()
        if not p:
            return {"error": "Player not found"}

        pd = db.query(PlayerData).filter(
            PlayerData.player_id == player_id,
            PlayerData.season == season,
        ).first()

        all_seasons = db.query(PlayerData).filter(PlayerData.player_id == player_id).all()
        team = db.query(Team).filter(Team.team_id == p.team_id).first()

        return {
            "player_id": p.player_id,
            "player_name": p.player_name,
            "player_name_en": p.player_name_en,
            "position": p.position,
            "jersey_number": p.jersey_number,
            "team_id": p.team_id,
            "team_name": team.team_name if team else "",
            "team_abbr": team.abbreviation if team else "",
            "age": p.age,
            "height": p.height,
            "weight": p.weight,
            "draft_year": p.draft_year,
            "experience": p.experience,
            "all_star_count": p.all_star_count,
            "player_role": p.player_role,
            "impact_score": p.impact_score,
            "offensive_impact": p.offensive_impact,
            "defensive_impact": p.defensive_impact,
            "injury_status": p.injury_status,
            "season_data": _player_data_dict(pd) if pd else None,
            "seasons": [_player_data_dict(s) for s in all_seasons],
        }


@router.get("/standings", summary="东西部排名")
async def get_standings(season: str = "2025-26"):
    with SessionLocal() as db:
        teams = db.query(Team).filter(Team.status == 1).all()
        team_map = {t.team_id: t for t in teams}

        standings = db.query(TeamData).filter(TeamData.season == season).all()

        east = []
        west = []
        for td in standings:
            t = team_map.get(td.team_id)
            if not t:
                continue
            entry = {
                "team_id": td.team_id,
                "abbreviation": t.abbreviation,
                "team_name": t.team_name,
                "wins": td.wins,
                "losses": td.losses,
                "win_percentage": td.win_percentage,
                "points_per_game": td.points_per_game,
                "opponent_points": td.opponent_points,
                "net_rating": td.net_rating,
                "recent_win_rate": td.recent_win_rate,
            }
            if t.conference and t.conference.lower() == "east":
                east.append(entry)
            else:
                west.append(entry)

        east.sort(key=lambda x: x["win_percentage"], reverse=True)
        west.sort(key=lambda x: x["win_percentage"], reverse=True)

        return {"east": east, "west": west}


@router.get("/games/today", summary="今日赛程")
async def get_today_games(days: int = 1):
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(max(1, min(days, 3)))]
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.game_date.in_(dates),
        ).order_by(GameRecord.game_date, GameRecord.game_id).all()

        team_ids = set()
        for g in games:
            team_ids.add(g.home_team_id)
            team_ids.add(g.away_team_id)

        teams = db.query(Team).filter(Team.team_id.in_(team_ids)).all() if team_ids else []
        team_map = {t.team_id: t for t in teams}

        return [
            {
                "game_id": g.game_id,
                "game_date": str(g.game_date),
                "home_team": team_map.get(g.home_team_id, {}).team_name if team_map.get(g.home_team_id) else "",
                "home_abbr": team_map.get(g.home_team_id, {}).abbreviation if team_map.get(g.home_team_id) else "",
                "away_team": team_map.get(g.away_team_id, {}).team_name if team_map.get(g.away_team_id) else "",
                "away_abbr": team_map.get(g.away_team_id, {}).abbreviation if team_map.get(g.away_team_id) else "",
                "home_score": g.home_score,
                "away_score": g.away_score,
                "status": g.status,
            }
            for g in games
        ]


@router.get("/games/upcoming", summary="今明两天赛程")
async def get_upcoming_games():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.game_date.in_([today, tomorrow]),
        ).order_by(GameRecord.game_date, GameRecord.game_id).all()

        team_ids = set()
        for g in games:
            team_ids.add(g.home_team_id)
            team_ids.add(g.away_team_id)

        teams = db.query(Team).filter(Team.team_id.in_(team_ids)).all() if team_ids else []
        team_map = {t.team_id: t for t in teams}

        return [
            {
                "game_id": g.game_id,
                "game_date": str(g.game_date),
                "home_team": team_map.get(g.home_team_id, {}).team_name if team_map.get(g.home_team_id) else "",
                "home_abbr": team_map.get(g.home_team_id, {}).abbreviation if team_map.get(g.home_team_id) else "",
                "away_team": team_map.get(g.away_team_id, {}).team_name if team_map.get(g.away_team_id) else "",
                "away_abbr": team_map.get(g.away_team_id, {}).abbreviation if team_map.get(g.away_team_id) else "",
                "home_score": g.home_score,
                "away_score": g.away_score,
                "status": g.status,
            }
            for g in games
        ]


@router.get("/games/recent", summary="近期比赛")
async def get_recent_games(days: int = 7, limit: int = 20):
    cutoff = date.today() - timedelta(days=days)
    with SessionLocal() as db:
        games = db.query(GameRecord).filter(
            GameRecord.game_date >= cutoff,
            GameRecord.status == "FINISHED",
        ).order_by(GameRecord.game_date.desc()).limit(limit).all()

        team_ids = set()
        for g in games:
            team_ids.add(g.home_team_id)
            team_ids.add(g.away_team_id)

        teams = db.query(Team).filter(Team.team_id.in_(team_ids)).all() if team_ids else []
        team_map = {t.team_id: t for t in teams}

        return [
            {
                "game_id": g.game_id,
                "game_date": str(g.game_date),
                "home_team": team_map.get(g.home_team_id, {}).team_name if team_map.get(g.home_team_id) else "",
                "home_abbr": team_map.get(g.home_team_id, {}).abbreviation if team_map.get(g.home_team_id) else "",
                "away_team": team_map.get(g.away_team_id, {}).team_name if team_map.get(g.away_team_id) else "",
                "away_abbr": team_map.get(g.away_team_id, {}).abbreviation if team_map.get(g.away_team_id) else "",
                "home_score": g.home_score,
                "away_score": g.away_score,
                "score_diff": g.score_diff,
            }
            for g in games
        ]


@router.get("/model/stats", summary="模型性能统计")
async def get_model_stats():
    with SessionLocal() as db:
        from app.db.models import AlgorithmParamSnapshot
        snapshots = db.query(AlgorithmParamSnapshot).order_by(
            AlgorithmParamSnapshot.created_at.desc()
        ).limit(5).all()

        player_count = db.query(Player).filter(Player.status == 1).count()
        team_count = db.query(Team).filter(Team.status == 1).count()
        game_count = db.query(GameRecord).filter(GameRecord.status == "FINISHED").count()
        pd_count = db.query(PlayerData).count()
        td_count = db.query(TeamData).count()

        return {
            "player_count": player_count,
            "team_count": team_count,
            "game_count": game_count,
            "player_data_count": pd_count,
            "team_data_count": td_count,
            "snapshots": [
                {
                    "id": s.id,
                    "version": s.version,
                    "description": s.description,
                    "created_at": str(s.created_at) if s.created_at else None,
                }
                for s in snapshots
            ],
        }


def _team_data_dict(td):
    return {
        "season": td.season,
        "wins": td.wins,
        "losses": td.losses,
        "win_percentage": td.win_percentage,
        "home_wins": td.home_wins,
        "home_losses": td.home_losses,
        "away_wins": td.away_wins,
        "away_losses": td.away_losses,
        "points_per_game": td.points_per_game,
        "assists_per_game": td.assists_per_game,
        "rebounds_per_game": td.rebounds_per_game,
        "turnovers_per_game": td.turnovers_per_game,
        "fg_percentage": td.fg_percentage,
        "three_percentage": td.three_percentage,
        "ft_percentage": td.ft_percentage,
        "steals_per_game": td.steals_per_game,
        "blocks_per_game": td.blocks_per_game,
        "opponent_points": td.opponent_points,
        "pace": td.pace,
        "offensive_rating": td.offensive_rating,
        "defensive_rating": td.defensive_rating,
        "net_rating": td.net_rating,
        "points_std": td.points_std,
        "recent_win_rate": td.recent_win_rate,
        "momentum": td.momentum,
        "home_ppg": td.home_ppg,
        "away_ppg": td.away_ppg,
    }


def _player_data_dict(pd):
    return {
        "season": pd.season,
        "games_played": pd.games_played,
        "minutes_per_game": pd.minutes_per_game,
        "points_per_game": pd.points_per_game,
        "rebounds_per_game": pd.rebounds_per_game,
        "assists_per_game": pd.assists_per_game,
        "steals_per_game": pd.steals_per_game,
        "blocks_per_game": pd.blocks_per_game,
        "turnovers_per_game": pd.turnovers_per_game,
        "fg_percentage": pd.fg_percentage,
        "three_percentage": pd.three_percentage,
        "ft_percentage": pd.ft_percentage,
        "true_shooting_pct": pd.true_shooting_pct,
        "effective_fg_pct": pd.effective_fg_pct,
        "usage_rate": pd.usage_rate,
        "assist_pct": pd.assist_pct,
        "rebound_pct": pd.rebound_pct,
        "steal_pct": pd.steal_pct,
        "block_pct": pd.block_pct,
        "turnover_pct": pd.turnover_pct,
        "points_std": pd.points_std,
        "points_cv": pd.points_cv,
        "offensive_rating": pd.offensive_rating,
        "defensive_rating": pd.defensive_rating,
        "net_rating": pd.net_rating,
    }
