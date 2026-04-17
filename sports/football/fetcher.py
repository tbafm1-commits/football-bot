import requests
import time
from datetime import datetime
from database.models import Session, Match, MatchStatistics, TeamStanding, init_db
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "http://api.isportsapi.com"


def api_request(path, params={}):
    params["api_key"] = API_KEY
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            time.sleep(0.5)
            return response.json()
        else:
            print(f"❌ API Error {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def fetch_today_fixtures():
    today = datetime.now().strftime("%Y-%m-%d")
    data = api_request("/sport/football/schedule", {"date": today})
    if not data:
        return []
    session = Session()
    for match in data.get("data", []):
        existing = session.query(Match).filter_by(api_id=match["matchId"]).first()
        match_date = datetime.strptime(match.get("matchTime", ""), "%Y-%m-%d %H:%M:%S") if match.get("matchTime") else datetime.now()
        if not existing:
            m = Match(
                api_id=match["matchId"],
                league_id=match.get("leagueId", 0),
                league_name=match.get("leagueName", ""),
                season=datetime.now().year,
                date=match_date,
                home_team_id=match.get("homeTeamId", 0),
                home_team_name=match.get("homeTeamName", ""),
                away_team_id=match.get("awayTeamId", 0),
                away_team_name=match.get("awayTeamName", ""),
                home_goals=match.get("homeScore"),
                away_goals=match.get("awayScore"),
                status=match.get("matchStatus", "NS"),
                venue=match.get("venueName", "")
            )
            session.add(m)
        else:
            existing.home_goals = match.get("homeScore")
            existing.away_goals = match.get("awayScore")
            existing.status = match.get("matchStatus", "NS")
    session.commit()
    session.close()
    print(f"✅ მატჩები განახლდა: {today}")


def fetch_all_standings():
    pass


def get_team_recent_matches(team_id, limit=5):
    session = Session()
    matches = session.query(Match).filter(
        ((Match.home_team_id == team_id) | (Match.away_team_id == team_id)),
        Match.status == "FT"
    ).order_by(Match.date.desc()).limit(limit).all()
    session.close()
    return matches


def get_h2h_matches(team1_id, team2_id, limit=5):
    session = Session()
    matches = session.query(Match).filter(
        ((Match.home_team_id == team1_id) & (Match.away_team_id == team2_id)) |
        ((Match.home_team_id == team2_id) & (Match.away_team_id == team1_id)),
        Match.status == "FT"
    ).order_by(Match.date.desc()).limit(limit).all()
    session.close()
    return matches


def fetch_odds(match_id):
    data = api_request("/sport/football/odds", {"matchId": match_id})
    if not data:
        return {}
    result = {
        "home": 0, "draw": 0, "away": 0,
        "over25": 0, "under25": 0,
        "btts_yes": 0, "btts_no": 0,
        "over85c": 0, "over95c": 0,
        "over25cards": 0, "over35cards": 0,
        "pen_yes": 0,
    }
    try:
        odds_data = data.get("data", {})
        europe = odds_data.get("europeOdds", {})
        result["home"] = float(europe.get("home", 0))
        result["draw"] = float(europe.get("draw", 0))
        result["away"] = float(europe.get("away", 0))
        over_under = odds_data.get("overUnder", {})
        result["over25"] = float(over_under.get("over", 0))
        result["under25"] = float(over_under.get("under", 0))
    except:
        pass
    return result
