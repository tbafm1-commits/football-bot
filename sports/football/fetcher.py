import requests
import time
from datetime import datetime, timedelta
from database.models import Session, Match, MatchStatistics, TeamStanding, init_db
from dotenv import load_dotenv
import os

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUES = {
    "Premier League":        "eng.1",
    "La Liga":               "esp.1",
    "Bundesliga":            "ger.1",
    "Serie A":               "ita.1",
    "Ligue 1":               "fra.1",
    "Eredivisie":            "ned.1",
    "Primeira Liga":         "por.1",
    "Scottish Prem":         "sco.1",
    "Super Lig":             "tur.1",
    "Champions League":      "uefa.champions",
    "Europa League":         "uefa.europa",
    "Conference League":     "uefa.europa.conf",
    "MLS":                   "usa.1",
    "Liga MX":               "mex.1",
    "Brazilian Serie A":     "bra.1",
    "Argentine Liga":        "arg.1",
    "Saudi Pro League":      "sau.1",
    "J1 League":             "jpn.1",
    "Championship":          "eng.2",
    "2. Bundesliga":         "ger.2",
}


def api_request(league_slug, date_str):
    url = f"{ESPN_BASE}/{league_slug}/scoreboard"
    try:
        response = requests.get(url, params={"dates": date_str}, timeout=15)
        if response.status_code == 200:
            time.sleep(0.3)
            return response.json()
        return None
    except Exception as e:
        print(f"Request failed ({league_slug}): {e}")
        return None


def fetch_today_fixtures(days_ahead=3):
    session = Session()
    count = 0

    for i in range(days_ahead):
        date = datetime.now() + timedelta(days=i)
        date_str = date.strftime("%Y%m%d")

        for league_name, slug in LEAGUES.items():
            data = api_request(slug, date_str)
            if not data:
                continue

            for event in data.get("events", []):
                try:
                    match_id = event["id"]
                    competitors = event["competitions"][0]["competitors"]
                    home = next(t for t in competitors if t["homeAway"] == "home")
                    away = next(t for t in competitors if t["homeAway"] == "away")

                    try:
                        match_date = datetime.strptime(event.get("date", ""), "%Y-%m-%dT%H:%MZ")
                    except:
                        match_date = datetime.now()

                    status = event.get("status", {}).get("type", {}).get("shortDetail", "NS")
                    home_score = home.get("score")
                    away_score = away.get("score")

                    existing = session.query(Match).filter_by(api_id=match_id).first()
                    if not existing:
                        m = Match(
                            api_id=match_id,
                            league_id=0,
                            league_name=league_name,
                            season=datetime.now().year,
                            date=match_date,
                            home_team_id=int(home["team"]["id"]),
                            home_team_name=home["team"]["displayName"],
                            away_team_id=int(away["team"]["id"]),
                            away_team_name=away["team"]["displayName"],
                            home_goals=int(home_score) if home_score else None,
                            away_goals=int(away_score) if away_score else None,
                            status=status,
                            venue=event["competitions"][0].get("venue", {}).get("fullName", "")
                        )
                        session.add(m)
                        count += 1
                    else:
                        existing.home_goals = int(home_score) if home_score else None
                        existing.away_goals = int(away_score) if away_score else None
                        existing.status = status

                except Exception as e:
                    print(f"Match parse error: {e}")
                    continue

    session.commit()
    session.close()
    print(f"fixtures ganakhlda: {count} axali match")


def fetch_all_standings():
    pass


def get_team_recent_matches(team_id, limit=10):
    session = Session()
    matches = session.query(Match).filter(
        ((Match.home_team_id == team_id) | (Match.away_team_id == team_id)),
        Match.status == "FT"
    ).order_by(Match.date.desc()).limit(limit).all()
    session.close()
    return matches


def get_h2h_matches(team1_id, team2_id, limit=6):
    session = Session()
    matches = session.query(Match).filter(
        ((Match.home_team_id == team1_id) & (Match.away_team_id == team2_id)) |
        ((Match.home_team_id == team2_id) & (Match.away_team_id == team1_id)),
        Match.status == "FT"
    ).order_by(Match.date.desc()).limit(limit).all()
    session.close()
    return matches


_odds_cache = {}


def fetch_all_odds():
    global _odds_cache
    if _odds_cache:
        return _odds_cache

    if not ODDS_API_KEY:
        print("ODDS_API_KEY ar aris")
        return {}

    try:
        url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h,totals",
            "bookmakers": "bet365",
            "dateFormat": "iso",
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Odds API error: {response.status_code}")
            return {}

        for game in response.json():
            home = game.get("home_team", "")
            away = game.get("away_team", "")
            if not home or not away:
                continue

            key = home.lower() + "_" + away.lower()
            result = {
                "home": 0, "draw": 0, "away": 0,
                "over25": 0, "under25": 0,
            }

            for bookmaker in game.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome["name"] == home:
                                result["home"] = float(outcome["price"])
                            elif outcome["name"] == away:
                                result["away"] = float(outcome["price"])
                            elif outcome["name"] == "Draw":
                                result["draw"] = float(outcome["price"])
                    elif market["key"] == "totals":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("point") == 2.5:
                                if outcome["name"] == "Over":
                                    result["over25"] = float(outcome["price"])
                                else:
                                    result["under25"] = float(outcome["price"])

            _odds_cache[key] = result

        print(f"odds: {len(_odds_cache)} match")
        return _odds_cache

    except Exception as e:
        print(f"Odds error: {e}")
        return {}


def fetch_odds(match_id):
    empty = {"home": 0, "draw": 0, "away": 0, "over25": 0, "under25": 0}

    session = Session()
    match = session.query(Match).filter_by(api_id=match_id).first()
    session.close()

    if not match or not match.home_team_name or not match.away_team_name:
        return empty

    all_odds = fetch_all_odds()
    key = match.home_team_name.lower() + "_" + match.away_team_name.lower()

    if key in all_odds:
        return all_odds[key]

    home_part = match.home_team_name.lower().split()[0]
    away_part = match.away_team_name.lower().split()[0]
    for k, v in all_odds.items():
        if home_part in k and away_part in k:
            return v

    return empty
