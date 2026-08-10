"""
系列赛服务 - 系列赛之星识别与赛季复盘
"""
from loguru import logger
from typing import Optional, List

from app.db.player_dao import PlayerDAO
from app.db.team_dao import TeamDAO
from app.db.config_dao import ConfigDAO
from config.settings import SERIES_STAR_CONFIG


class SeriesService:

    def __init__(self):
        self.player_dao = PlayerDAO()
        self.team_dao = TeamDAO()
        self.config_dao = ConfigDAO()

    def identify_stars(self, season: str, team_id: Optional[int] = None) -> List[dict]:
        """
        识别系列赛之星
        从series_star表读取已识别的季后赛之星
        """
        from app.db.database import SessionLocal
        from app.db.models import SeriesStar, Player

        with SessionLocal() as db:
            query = db.query(SeriesStar, Player).join(
                Player, SeriesStar.player_id == Player.player_id
            ).filter(
                SeriesStar.season == season,
                SeriesStar.is_star == 1,
            )
            if team_id:
                query = query.filter(SeriesStar.team_id == team_id)

            results = query.order_by(SeriesStar.score_up.desc()).all()

        stars = []
        for ss, player in results:
            team = self.team_dao.get_team(player.team_id) if player.team_id else None
            stars.append({
                "star_id": ss.star_id,
                "player_id": ss.player_id,
                "player_name": player.player_name,
                "team_name": team.team_name if team else "未知",
                "avg_score": round(ss.avg_score, 1),
                "avg_fg_pct": round(ss.avg_fg_pct, 3),
                "score_up": round(ss.score_up, 1),
                "hit_rate_up": round(ss.hit_rate_up, 3),
                "key_game_score": ss.key_game_score or 0,
            })

        return stars

    def get_review(self, season: str, team_id: Optional[int] = None) -> dict:
        """
        全赛季复盘

        复盘内容:
        - 系列赛概况
        - 关键比赛统计
        - 球员表现汇总
        """
        from app.db.database import SessionLocal
        from app.db.models import GameRecord

        with SessionLocal() as db:
            game_query = db.query(GameRecord).filter(GameRecord.season == season)
            if team_id:
                game_query = game_query.filter(
                    (GameRecord.home_team_id == team_id) | (GameRecord.away_team_id == team_id)
                )
            games = game_query.order_by(GameRecord.game_date.desc()).all()

        total_games = len(games)
        playoff_games = sum(1 for g in games if g.is_playoff)

        total_score = sum((g.total_score or 0) for g in games)
        avg_total = round(total_score / total_games, 1) if total_games > 0 else 0

        home_wins = sum(1 for g in games if g.home_win)
        away_wins = total_games - home_wins

        close_games = sum(1 for g in games if g.score_diff and abs(g.score_diff) <= 5)

        stars = self.identify_stars(season, team_id)

        team_name = "全部球队"
        if team_id:
            team = self.team_dao.get_team(team_id)
            if team:
                team_name = team.team_name

        return {
            "season": season,
            "team_id": team_id,
            "team_name": team_name,
            "total_games": total_games,
            "playoff_games": playoff_games,
            "avg_total_score": avg_total,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "close_games": close_games,
            "close_game_rate": round(close_games / total_games, 3) if total_games > 0 else 0,
            "star_players": stars[:10],
            "series_count": max(1, playoff_games // 4) if playoff_games > 0 else 0,
        }

    def get_player_series_stats(self, player_id: int, season: str) -> dict:
        """获取球员系列赛数据"""
        player = self.player_dao.get_player(player_id)
        if not player:
            return {"player_id": player_id, "error": "球员不存在"}

        pdata = self.player_dao.get_player_data(player_id, season)
        if not pdata:
            return {"player_id": player_id, "error": "无赛季数据"}

        base_score = pdata.points_per_game or 0
        base_fg = pdata.fg_percentage or 0

        return {
            "player_id": player_id,
            "player_name": player.player_name,
            "season": season,
            "regular_season": {
                "avg_score": base_score,
                "avg_fg_pct": base_fg,
                "games_played": pdata.games_played or 0,
            },
            "series_boost": {
                "score_up": round(base_score * 0.15, 1),
                "hit_rate_up": round(base_fg * 0.10, 3),
            },
        }
