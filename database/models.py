from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

db_url = os.getenv("DATABASE_URL", "sqlite:///football.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    api_id = Column(Integer, unique=True)
    name = Column(String(100))
    league_id = Column(Integer)
    country = Column(String(50))


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    api_id = Column(Integer, unique=True)
    league_id = Column(Integer)
    league_name = Column(String(100))
    season = Column(Integer)
    date = Column(DateTime)
    home_team_id = Column(Integer)
    home_team_name = Column(String(100))
    away_team_id = Column(Integer)
    away_team_name = Column(String(100))
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    status = Column(String(20))
    venue = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchStatistics(Base):
    __tablename__ = "match_statistics"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer)
    team_id = Column(Integer)
    shots_on_goal = Column(Integer, default=0)
    shots_total = Column(Integer, default=0)
    possession = Column(Float, default=0)
    corners = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    offsides = Column(Integer, default=0)
    passes_accuracy = Column(Float, default=0)


class TeamStanding(Base):
    __tablename__ = "standings"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer)
    season = Column(Integer)
    team_id = Column(Integer)
    team_name = Column(String(100))
    rank = Column(Integer)
    points = Column(Integer)
    played = Column(Integer)
    won = Column(Integer)
    drawn = Column(Integer)
    lost = Column(Integer)
    goals_for = Column(Integer)
    goals_against = Column(Integer)
    goal_diff = Column(Integer)
    form = Column(String(20))
    updated_at = Column(DateTime, default=datetime.utcnow)


class BettingTip(Base):
    __tablename__ = "betting_tips"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer)
    match_date = Column(DateTime)
    home_team = Column(String(100))
    away_team = Column(String(100))
    league_name = Column(String(100))
    tip_type = Column(String(50))
    tip_value = Column(String(50))
    confidence = Column(Float)
    reasoning = Column(Text)
    result = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
    print("Database initialized!")


if __name__ == "__main__":
    init_db()
