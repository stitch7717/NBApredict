"""
球员数据访问
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import Player, PlayerData, GameRecord
from app.db.database import SessionLocal


class PlayerDAO:

    def get_session(self) -> Session:
        return SessionLocal()

    def get_player(self, player_id: int) -> Optional[Player]:
        with self.get_session() as db:
            return db.query(Player).filter(Player.player_id == player_id).first()

    def get_player_data(self, player_id: int, season: str) -> Optional[PlayerData]:
        with self.get_session() as db:
            return db.query(PlayerData).filter(
                PlayerData.player_id == player_id,
                PlayerData.season == season
            ).first()

    def get_player_recent_games(self, player_id: int, limit: int = 20) -> List[GameRecord]:
        """获取球员所在球队的最近比赛"""
        with self.get_session() as db:
            player = db.query(Player).filter(Player.player_id == player_id).first()
            if not player or not player.team_id:
                return []
            return db.query(GameRecord).filter(
                (GameRecord.home_team_id == player.team_id) |
                (GameRecord.away_team_id == player.team_id)
            ).order_by(GameRecord.game_date.desc()).limit(limit).all()

    def get_all_active_players(self) -> List[Player]:
        with self.get_session() as db:
            return db.query(Player).filter(Player.status == 1).all()

    def get_players_with_data(self, season: str) -> List[dict]:
        """获取有赛季数据的球员列表"""
        with self.get_session() as db:
            results = db.query(Player, PlayerData).join(
                PlayerData, Player.player_id == PlayerData.player_id
            ).filter(
                Player.status == 1,
                PlayerData.season == season,
                PlayerData.games_played >= 10
            ).all()
            return [{"player": p, "data": d} for p, d in results]

    def update_player_cluster(self, player_id: int, cluster_id: int, cluster_name: str):
        with self.get_session() as db:
            player = db.query(Player).filter(Player.player_id == player_id).first()
            if player:
                player.cluster_id = cluster_id
                player.cluster_name = cluster_name
                db.commit()
