import traceback
from datetime import datetime
from database.models import Session, Match, TeamStanding
from sports.football.fetcher import (
    fetch_today_fixtures,
    get_team_recent_matches,
    get_h2h_matches,
    fetch_odds,
)
from core.logic import TeamStats, H2HStats, RefereeStats, get_all_markets


def get_referee_stats(fixture_id):
    return RefereeStats()


def build_team_stats(team_id, team_name, is_home, league_id, season):
    recent = get_team_recent_matches(team_id, limit=10)
    session = Session()

    goals_scored, goals_conceded = [], []
    home_goals_scored, home_goals_conceded = [], []
    away_goals_scored, away_goals_conceded = [], []
    home_results, away_results = [], []
    games_played_home = games_played_away = 0
    clean_sheets_home = clean_sheets_away = 0

    for match in recent:
        is_home_team = match.home_team_id == team_id
        scored = match.home_goals if is_home_team else match.away_goals
        conceded = match.away_goals if is_home_team else match.home_goals
        if scored is None or conceded is None:
            continue

        goals_scored.append(scored)
        goals_conceded.append(conceded)
        result = "W" if scored > conceded else ("D" if scored == conceded else "L")

        if is_home_team:
            home_goals_scored.append(scored)
            home_goals_conceded.append(conceded)
            games_played_home += 1
            if conceded == 0:
                clean_sheets_home += 1
            home_results.append(result)
        else:
            away_goals_scored.append(scored)
            away_goals_conceded.append(conceded)
            games_played_away += 1
            if conceded == 0:
                clean_sheets_away += 1
            away_results.append(result)

    rank, points, played = 10, 20, max(games_played_home + games_played_away, 1)
    standing = session.query(TeamStanding).filter_by(
        team_id=team_id, league_id=league_id, season=season
    ).first()
    if standing:
        rank = standing.rank
        points = standing.points
        played = max(standing.played, 1)

    session.close()

    return TeamStats(
        team_id=team_id,
        team_name=team_name,
        is_home=is_home,
        goals_scored=goals_scored,
        goals_conceded=goals_conceded,
        home_goals_scored=home_goals_scored,
        home_goals_conceded=home_goals_conceded,
        away_goals_scored=away_goals_scored,
        away_goals_conceded=away_goals_conceded,
        corners_for=[],
        corners_against=[],
        yellow_cards=[],
        fouls_committed=[],
        home_results=home_results,
        away_results=away_results,
        rank=rank,
        points=points,
        played=played,
        games_played_home=max(games_played_home, 1),
        games_played_away=max(games_played_away, 1),
        clean_sheets_home=clean_sheets_home,
        clean_sheets_away=clean_sheets_away,
    )


def build_h2h_stats(home_id, away_id):
    matches = get_h2h_matches(home_id, away_id, limit=5)
    h2h = H2HStats()
    for match in matches:
        if match.home_goals is None:
            continue
        h2h.matches.append({
            "home_id": match.home_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
        })
    return h2h


async def get_todays_bet_options():
    session = Session()
    today = datetime.now().date()

    matches = session.query(Match).filter(
        Match.date >= datetime.combine(today, datetime.min.time()),
        Match.date < datetime.combine(today, datetime.max.time()),
        Match.status != "FT"
    ).all()
    session.close()

    if not matches:
        fetch_today_fixtures()
        session = Session()
        matches = session.query(Match).filter(
            Match.date >= datetime.combine(today, datetime.min.time()),
            Match.date < datetime.combine(today, datetime.max.time()),
        ).all()
        session.close()

    print(f"DB matches: {len(matches)}")
    all_options = []
    season = today.year if today.month >= 7 else today.year - 1

    for match in matches:
        try:
            home_stats = build_team_stats(
                match.home_team_id, match.home_team_name,
                True, match.league_id, season
            )
            away_stats = build_team_stats(
                match.away_team_id, match.away_team_name,
                False, match.league_id, season
            )
            h2h = build_h2h_stats(match.home_team_id, match.away_team_id)
            odds = fetch_odds(match.api_id)
            kick_off = match.date.strftime("%H:%M") if match.date else "?"

            options = get_all_markets(
                match_id=match.api_id,
                home=home_stats,
                away=away_stats,
                h2h=h2h,
                ref=get_referee_stats(match.api_id),
                odds=odds,
                kick_off=kick_off,
                league=match.league_name,
            )
            all_options.extend(options)

        except Exception as e:
            print(f"ERROR: {traceback.format_exc()}")
            continue

    all_options.sort(key=lambda x: x.our_prob, reverse=True)
    print(f"options: {len(all_options)}")
    return all_options
