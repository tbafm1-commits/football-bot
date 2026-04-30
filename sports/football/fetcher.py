import requests
import time
from datetime import datetime, timedelta
from database.models import Session, Match, TeamStanding
from dotenv import load_dotenv
import os

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUES = {
    "Premier League":           "eng.1",
    "La Liga":                  "esp.1",
    "Bundesliga":               "ger.1",
    "Serie A":                  "ita.1",
    "Ligue 1":                  "fra.1",
    "Eredivisie":               "ned.1",
    "Primeira Liga":            "por.1",
    "Scottish Prem":            "sco.1",
    "Super Lig":                "tur.1",
    "Belgian Pro League":       "bel.1",
    "Russian Premier League":   "rus.1",
    "Greek Super League":       "gre.1",
    "Austrian Bundesliga":      "aut.1",
    "Swiss Super League":       "sui.1",
    "Danish Superliga":         "den.1",
    "Norwegian Eliteserien":    "nor.1",
    "Swedish Allsvenskan":      "swe.1",
    "Polish Ekstraklasa":       "pol.1",
    "Czech First League":       "cze.1",
    "Romanian Liga 1":          "rou.1",
    "Croatian HNL":             "cro.1",
    "Championship":             "eng.2",
    "League One":               "eng.3",
    "2. Bundesliga":            "ger.2",
    "Serie B":                  "ita.2",
    "La Liga 2":                "esp.2",
    "Champions League":         "uefa.champions",
    "Europa League":            "uefa.europa",
    "Conference League":        "uefa.europa.conf",
    "Nations League":           "uefa.nations",
    "MLS":                      "usa.1",
    "Liga MX":                  "mex.1",
    "Brazilian Serie A":        "bra.1",
    "Brazilian Serie B":        "bra.2",
    "Argentine Liga":           "arg.1",
    "Colombian Primera A":      "col.1",
    "Chilean Primera":          "chi.1",
    "Ecuadorian Serie A":       "ecu.1",
    "Uruguayan PD":             "uru.1",
    "Copa Libertadores":        "conmebol.libertadores",
    "Copa Sudamericana":        "conmebol.sudamericana",
    "Saudi Pro League":         "sau.1",
    "UAE Pro League":           "uae.1",
    "Qatar Stars League":       "qat.1",
    "J1 League":                "jpn.1",
    "K League 1":               "kor.1",
    "Chinese Super League":     "chn.1",
    "A-League":                 "aus.1",
    "World Cup":                "fifa.world",
    "Copa America":             "conmebol.america",
    "Africa Cup of Nations":    "caf.nations",
}


def _get_team_id(team):
    tid = team.get("id", 0)
    if isinstance(tid, dict):
        return int(tid.get("value", 0) or 0)
    try:
        return int(tid or 0)
    except:
        return 0


def _get_score(score):
    if score is None:
        return None
    if isinstance(score, dict):
        try:
            return int(float(score.get("value", 0) or 0))
        except:
            return None
    try:
        return int(float(score))
    except:
        return None


def _scoreboard_request(league_slug, date_str):
    url = f"{ESPN_BASE}/{league_slug}/scoreboard"
    try:
        response = requests.get(url, params={"dates": date_str}, timeout=15)
        if response.status_code == 200:
            time.sleep(0.3)
            return response.json()
        return None
    except Exception as e:
        print(f"scoreboard error ({league_slug}): {e}")
        return None


def _save_match(session, event, league_name, status_override=None):
    try:
        match_id = event["id"]
        competitors = event["competitions"][0]["competitors"]
        home = next(t for t in competitors if t["homeAway"] == "home")
        away = next(t for t in competitors if t["homeAway"] == "away")

        try:
            match_date = datetime.strptime(event.get("date", ""), "%Y-%m-%dT%H:%MZ")
        except:
            match_date = datetime.now()

        completed = event["competitions"][0].get("status", {}).get("type", {}).get("completed", False)
        status = status_override or ("FT" if completed else event.get("status", {}).get("type", {}).get("shortDetail", "NS"))

        existing = session.query(Match).filter_by(api_id=match_id).first()
        if not existing:
            m = Match(
                api_id=match_id,
                league_id=0,
                league_name=league_name,
                season=datetime.now().year,
                date=match_date,
                home_team_id=_get_team_id(home["team"]),
                home_team_name=home["team"]["displayName"],
                away_team_id=_get_team_id(away["team"]),
                away_team_name=away["team"]["displayName"],
                home_goals=_get_score(home.get("score")),
                away_goals=_get_score(away.get("score")),
                status=status,
                venue=event["competitions"][0].get("venue", {}).get("fullName", "")
            )
            session.add(m)
            return True
        else:
            existing.home_goals = _get_score(home.get("score"))
            existing.away_goals = _get_score(away.get("score"))
            existing.status = status
            return False
    except Exception as e:
        print(f"save_match error: {e}")
        return False


def fetch_today_fixtures(days_ahead=3):
    session = Session()
    count = 0

    for i in range(days_ahead):
        date = datetime.now() + timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        for league_name, slug in LEAGUES.items():
            data = _scoreboard_request(slug, date_str)
            if not data:
                continue
            for event in data.get("events", []):
                if _save_match(session, event, league_name):
                    count += 1

    session.commit()

    today = datetime.now().date()
    upcoming = session.query(Match).filter(
        Match.date >= datetime.combine(today, datetime.min.time()),
        Match.date < datetime.combine(today + timedelta(days=days_ahead), datetime.min.time()),
        Match.status != "FT"
    ).all()
    session.close()

    print(f"fixtures: {count} axali match")

    for match in upcoming:
        slug = LEAGUES.get(match.league_name, "eng.1")
        fetch_team_history(match.home_team_id, slug)
        fetch_team_history(match.away_team_id, slug)
        fetch_h2h_history(match.home_team_id, match.away_team_id, slug)
        time.sleep(0.5)

    print("istoria da h2h ganakhlda!")


def fetch_team_history(team_id, league_slug, limit=10):
    url = f"{ESPN_BASE}/{league_slug}/teams/{team_id}/schedule"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return
        data = response.json()
        session = Session()

        events = data.get("events", [])
        finished = [
            e for e in events
            if e.get("competitions", [{}])[0]
            .get("status", {}).get("type", {}).get("completed", False)
        ]

        added = 0
        for event in finished[-limit:]:
            if _save_match(session, event, "", status_override="FT"):
                added += 1

        session.commit()
        session.close()
        if added:
            print(f"team {team_id}: {added} history match")

    except Exception as e:
        print(f"fetch_team_history error ({team_id}): {e}")


def fetch_h2h_history(home_id, away_id, league_slug, limit=5):
    url = f"{ESPN_BASE}/{league_slug}/teams/{home_id}/schedule"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return
        data = response.json()
        session = Session()

        h2h_events = []
        for event in data.get("events", []):
            try:
                competitors = event["competitions"][0]["competitors"]
                ids = [_get_team_id(t["team"]) for t in competitors]
                completed = event["competitions"][0].get("status", {}).get("type", {}).get("completed", False)
                if away_id in ids and completed:
                    h2h_events.append(event)
            except:
                continue

        added = 0
        for event in h2h_events[-limit:]:
            if _save_match(session, event, "H2H", status_override="FT"):
                added += 1

        session.commit()
        session.close()
        if added:
            print(f"H2H {home_id} vs {away_id}: {added} match")

    except Exception as e:
        print(f"fetch_h2h_history error: {e}")


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


def get_h2h_matches(team1_id, team2_id, limit=5):
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
            result = {"home": 0, "draw": 0, "away": 0, "over25": 0, "under25": 0}

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
