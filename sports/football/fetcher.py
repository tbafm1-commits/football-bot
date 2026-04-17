import requests
import time
from datetime import datetime
from database.models import Session, Match, MatchStatistics, TeamStanding, init_db
import os
from dotenv import load_dotenv

load_dotenv()

ISPORTS_KEY = os.getenv("API_FOOTBALL_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ISPORTS_BASE = "http://api.isportsapi.com"
ODDS_BASE = "https://api.the-odds-api.com/v4"


def api_request(path, params={}):
    p = dict(params)
    p["api_key"] = ISPORTS_KEY
    url = ISPORTS_BASE + path
    try:
        response = requests.get(url, params=p, timeout=15)
        if response.status_code == 200:
            time.sleep(0.5)
            return response.json()
        else:
            print("API Error " + str(response.status_code))
            return None
    except Exception as e:
        print("Request failed: " + str(e))
        return None


def fetch_today_fixtures():
    today = datetime.now().strftime("%Y-%m-%d")
    data = api_request("/sport/football/schedule", {"date": today})
    if not data:
        return []
    session = Session()
    count = 0
    for match in data.get("data", []):
        existing = session.query(Match).filter_by(api_id=match["matchId"]).first()
        mt = match.get("matchTime")
        if mt and isinstance(mt, str):
            try:
                match_date = datetime.strptime(mt, "%Y-%m-%d %H:%M:%S")
            except:
                match_date = datetime.now()
        else:
            match_date = datetime.now()

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
                status=str(match.get("matchStatus", "NS")),
                venue=match.get("venueName", "")
            )
            session.add(m)
            count += 1
        else:
            existing.home_goals = match.get("homeScore")
            existing.away_goals = match.get("awayScore")
            existing.status = str(match.get("matchStatus", "NS"))
    session.commit()
    session.close()
    print("matchebi ganakhlda: " + today + " (" + str(count) + ")")


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


# odds cache - ar gamoivwviot zedmet requestebs
_odds_cache = {}


def fetch_all_odds():
    global _odds_cache
    if _odds_cache:
        return _odds_cache

    try:
        url = ODDS_BASE + "/sports/soccer/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h,totals",
            "bookmakers": "bet365",
            "dateFormat": "iso",
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print("Odds API error: " + str(response.status_code))
            return {}

        data = response.json()
        for game in data:
            home = game.get("home_team", "")
            away = game.get("away_team", "")
            key = home.lower() + "_" + away.lower()

            result = {
                "home": 0, "draw": 0, "away": 0,
                "over25": 0, "under25": 0,
                "over35": 0, "under35": 0,
                "btts_yes": 0, "btts_no": 0,
                "over85c": 0, "over95c": 0,
                "over25cards": 0, "over35cards": 0,
                "pen_yes": 0,
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
                            point = outcome.get("point", 0)
                            name = outcome["name"]
                            if point == 2.5:
                                if name == "Over":
                                    result["over25"] = float(outcome["price"])
                                else:
                                    result["under25"] = float(outcome["price"])
                            elif point == 3.5:
                                if name == "Over":
                                    result["over35"] = float(outcome["price"])
                                else:
                                    result["under35"] = float(outcome["price"])

            _odds_cache[key] = result

        print("odds chamoitvirtha: " + str(len(_odds_cache)) + " match")
        return _odds_cache

    except Exception as e:
        print("Odds fetch error: " + str(e))
        return {}


def fetch_odds(match_id):
    result = {
        "home": 0, "draw": 0, "away": 0,
        "over25": 0, "under25": 0,
        "over35": 0, "under35": 0,
        "btts_yes": 0, "btts_no": 0,
        "over85c": 0, "over95c": 0,
        "over25cards": 0, "over35cards": 0,
        "pen_yes": 0,
    }

    session = Session()
    match = session.query(Match).filter_by(api_id=match_id).first()
    session.close()

    if not match:
        return result

    all_odds = fetch_all_odds()
    key = match.home_team_name.lower() + "_" + match.away_team_name.lower()

    if key in all_odds:
        return all_odds[key]

    # partial match
    for k, v in all_odds.items():
        home_part = match.home_team_name.lower().split()[0]
        away_part = match.away_team_name.lower().split()[0]
        if home_part in k and away_part in k:
            return v

    return result
