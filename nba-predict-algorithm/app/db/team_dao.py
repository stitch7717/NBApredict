"""
球队数据访问
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import Team, TeamData, GameRecord, BattleRecord, OddsData
from app.db.database import SessionLocal


class TeamDAO:

    def get_session(self) -> Session:
        return SessionLocal()

    def get_team(self, team_id: int) -> Optional[Team]:
        with self.get_session() as db:
            return db.query(Team).filter(Team.team_id == team_id).first()

    def get_team_data(self, team_id: int, season: str) -> Optional[TeamData]:
        with self.get_session() as db:
            return db.query(TeamData).filter(
                TeamData.team_id == team_id,
                TeamData.season == season
            ).first()

    def get_battle_record(self, team1_id: int, team2_id: int, season: str = None) -> List[BattleRecord]:
        with self.get_session() as db:
            query = db.query(BattleRecord).filter(
                ((BattleRecord.team1_id == team1_id) & (BattleRecord.team2_id == team2_id)) |
                ((BattleRecord.team1_id == team2_id) & (BattleRecord.team2_id == team1_id))
            )
            if season:
                query = query.filter(BattleRecord.season == season)
            return query.order_by(BattleRecord.season.desc()).all()

    def get_head_to_head_games(self, team1_id: int, team2_id: int, limit: int = 10) -> List[GameRecord]:
        with self.get_session() as db:
            return db.query(GameRecord).filter(
                ((GameRecord.home_team_id == team1_id) & (GameRecord.away_team_id == team2_id)) |
                ((GameRecord.home_team_id == team2_id) & (GameRecord.away_team_id == team1_id))
            ).order_by(GameRecord.game_date.desc()).limit(limit).all()

    def get_recent_games(self, team_id: int, limit: int = 10) -> List[GameRecord]:
        with self.get_session() as db:
            return db.query(GameRecord).filter(
                (GameRecord.home_team_id == team_id) | (GameRecord.away_team_id == team_id)
            ).order_by(GameRecord.game_date.desc()).limit(limit).all()

    def get_all_teams(self) -> List[Team]:
        with self.get_session() as db:
            return db.query(Team).filter(Team.status == 1).all()

    def get_teams_with_data(self, season: str) -> List[dict]:
        with self.get_session() as db:
            results = db.query(Team, TeamData).join(
                TeamData, Team.team_id == TeamData.team_id
            ).filter(
                Team.status == 1,
                TeamData.season == season
            ).all()
            return [{"team": t, "data": d} for t, d in results]

    def update_team_cluster(self, team_id: int, cluster_type: str, cluster_id: int, cluster_name: str):
        with self.get_session() as db:
            team = db.query(Team).filter(Team.team_id == team_id).first()
            if team:
                if cluster_type == "defense":
                    team.defense_cluster = cluster_id
                    team.defense_type = cluster_name
                else:
                    team.offense_cluster = cluster_id
                    team.offense_type = cluster_name
                db.commit()

    def get_latest_odds(self, home_team_id: int, away_team_id: int) -> Optional[OddsData]:
        with self.get_session() as db:
            return db.query(OddsData).filter(
                OddsData.home_team_id == home_team_id,
                OddsData.away_team_id == away_team_id
            ).order_by(OddsData.game_date.desc()).first()

    def get_recent_back_to_back(self, team_id: int) -> bool:
        """检查球队是否处于背靠背"""
        games = self.get_recent_games(team_id, limit=2)
        if len(games) < 2:
            return False
        from datetime import timedelta
        diff = abs((games[0].game_date - games[1].game_date).days)
        return diff <= 1
