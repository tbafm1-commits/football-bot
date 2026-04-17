import requests
import time
from datetime import datetime, timedelta
from database.models import Session, Match, MatchStatistics, TeamStanding, Team, init_db
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

TRACKED_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "UEFA Champions League",
    3: "UEFA Europa League",
}

HEADERS = {"x-apisports-key": API_KEY}


def api_request(endpoint, params={}):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if response.status_code == 200:
            time.sleep(0.5)
            return response.json()
        elif response.status_code == 429:
            print("⚠️ Rate limit! 60 წამი...")
            time.sleep(60)
            return api_request(endpoint, params)
        else:
            print(f"❌ API Error {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def fetch_fixtures(league_id, season, date=None):
    params = {"league": league_id, "season": season}
    if date:
        params["date"] = date
    data = api_request("fixtures", params)
    if not data:
        return []
    session = Session()
    fixtures = []
    for fixture in data.get("response", []):
        fix = fixture["fixture"]
        teams = fixture["teams"]
        goals = fixture["goals"]
        league = fixture["league"]
        match_date = datetime.fromisoformat(fix["date"].replace("Z", "+00:00"))
        existing = session.query(Match).filter_by(api_id=fix["id"]).first()
        if existing:
            existing.home_goals = goals.get("home")
            existing.away_goals = goals.get("away")
            existing.status = fix["status"]["short"]
            existing.updated_at = datetime.utcnow()
        else:
            match = Match(
                api_id=fix["id"], league_id=league["id"],
                league_name=league["name"], season=league["season"],
                date=match_date, home_team_id=teams["home"]["id"],
                home_team_name=teams["home"]["name"],
                away_team_id=teams["away"]["id"],
                away_team_name=teams["away"]["name"],
                home_goals=goals.get("home"), away_goals=goals.get("away"),
                status=fix["status"]["short"],
                venue=fix.get("venue", {}).get("name", "Unknown")
            )
            session.add(match)
            fixtures.append(match)
    session.commit()
    session.close()
    return fixtures


def fetch_standings(league_id, season):
    data = api_request("standings", {"league": league_id, "season": season})
    if not data:
        return False
    session = Session()
    try:
        standings_data = data["response"][0]["league"]["standings"][0]
    except (IndexError, KeyError):
        return False
    for team_data in standings_data:
        team = team_data["team"]
        all_stats = team_data["all"]
        goals = all_stats["goals"]
        existing = session.query(TeamStanding).filter_by(
            league_id=league_id, season=season, team_id=team["id"]
        ).first()
        sd = {
            "team_name": team["name"], "rank": team_data["rank"],
            "points": team_data["points"], "played": all_stats["played"],
            "won": all_stats["win"], "drawn": all_stats["draw"],
            "lost": all_stats["lose"], "goals_for": goals["for"],
            "goals_against": goals["against"],
            "goal_diff": team_data["goalsDiff"],
            "form": team_data.get("form", ""),
            "updated_at": datetime.utcnow()
        }
        if existing:
            for k, v in sd.items():
                setattr(existing, k, v)
        else:
            session.add(TeamStanding(league_id=league_id, season=season, team_id=team["id"], **sd))
    session.commit()
    session.close()
    return True


def fetch_today_fixtures():
    today = datetime.now().strftime("%Y-%m-%d")
    season = datetime.now().year
    for league_id, league_name in TRACKED_LEAGUES.items():
        print(f"⚽ {league_name}...")
        fetch_fixtures(league_id, season, today)


def fetch_all_standings():
    season = datetime.now().year
    for league_id, league_name in TRACKED_LEAGUES.items():
        fetch_standings(league_id, season)


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

