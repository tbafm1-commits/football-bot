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
    "Premier League":      "eng.1",
    "La Liga":             "esp.1",
    "Bundesliga":          "ger.1",
    "Serie A":             "ita.1",
    "Ligue 1":             "fra.1",
    "Eredivisie":          "ned.1",
    "Primeira Liga":       "por.1",
    "Scottish Prem":       "sco.1",
    "Super Lig":           "tur.1",
    "Champions League":    "uefa.champions",
    "Europa League":       "uefa.europa",
    "Conference League":   "uefa.europa.conf",
    "MLS":                 "usa.1",
    "Liga MX":             "mex.1",
    "Brazilian Serie A":   "bra.1",
    "Argentine Liga":      "arg.1",
    "Saudi Pro League":    "sau.1",
    "J1 League":           "jpn.1",
    "Championship":        "eng.2",
    "2. Bundesliga":       "ger.2",
}


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
                home_goals=int(home_score) if home_score is not None else None,
                away_goals=int(away_score) if away_score is not None else None,
                status=status,
                venue=event["competitions"][0].get("venue", {}).get("fullName", "")
            )
            session.add(m)
            return True
        else:
            existing.home_goals = int(home_score) if home_score is not None else None
            existing.away_goals = int(away_score) if away_score is not None else None
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

    # მომავალი მატჩების ისტორია
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
                ids = [int(t["team"]["id"]) for t in competitors]
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
            "dateFormat": "iso
