from datetime import datetime
from database.models import Session, Match, MatchStatistics, TeamStanding
from sports.football.fetcher import (
    fetch_today_fixtures,
    get_team_recent_matches,
    get_h2h_matches,
    api_request,
    fetch_odds,
)
from core.logic import (
    TeamStats, H2HStats, RefereeStats,
    BetOption, get_all_markets
)


def get_referee_stats(fixture_id):
    return RefereeStats()


def build_team_stats(team_id, team_name, is_home, league_id, season):
    recent = get_team_recent_matches(team_id, limit=10)

    stats = TeamStats(
        team_id=team_id,
        team_name=team_name,
        is_home=is_home,
        goals_scored=[1, 1, 1, 1, 1],
        goals_conceded=[1, 1, 1, 1, 1],
        home_goals_scored=[1, 1, 1, 1, 1],
        home_goals_conceded=[1, 1, 1, 1, 1],
        away_goals_scored=[1, 1, 1, 1, 1],
        away_goals_conceded=[1, 1, 1, 1, 1],
        corners_for=[5, 5, 5, 5, 5],
        corners_against=[5, 5, 5, 5, 5],
        yellow_cards=[2, 2, 2, 2, 2],
        fouls_committed=[12, 12, 12, 12, 12],
        home_results=["W", "D", "W", "L", "W"],
        away_results=["W", "D", "L", "W", "D"],
        rank=10,
        points=20,
        played=20,
        games_played_home=10,
        games_played_away=10,
        clean_sheets_home=3,
        clean_sheets_away=2,
    )

    session = Session()

    for match in recent:
        is_home_team = match.home_team_id == team_id
        scored = match.home_goals if is_home_team else match.away_goals
        conceded = match.away_goals if is_home_team else match.home_goals

        if scored is None or conceded is None:
            continue

        stats.goals_scored.append(scored)
        stats.goals_conceded.append(conceded)

        if is_home_team:
            stats.home_goals_scored.append(scored)
            stats.home_goals_conceded.append(conceded)
            stats.games_played_home += 1
            if conceded == 0:
                stats.clean_sheets_home += 1
            result = "W" if scored > conceded else ("D" if scored == conceded else "L")
            stats.home_results.append(result)
        else:
            stats.away_goals_scored.append(scored)
            stats.away_goals_conceded.append(conceded)
            stats.games_played_away += 1
            if conceded == 0:
                stats.clean_sheets_away += 1
            result = "W" if scored > conceded else ("D" if scored == conceded else "L")
            stats.away_results.append(result)

        match_stat = session.query(MatchStatistics).filter_by(
            match_id=match.api_id, team_id=team_id
        ).first()

        if match_stat:
            stats.corners_for.append(int(match_stat.corners or 0))
            stats.yellow_cards.append(int(match_stat.yellow_cards or 0))
            stats.red_cards.append(int(match_stat.red_cards or 0))
            stats.fouls_committed.append(int(match_stat.fouls or 0))

    standing = session.query(TeamStanding).filter_by(
        team_id=team_id, league_id=league_id, season=season
    ).first()

    if standing:
        stats.rank = standing.rank
        stats.points = standing.points
        stats.played = max(standing.played, 1)

    session.close()
    return stats


def build_h2h_stats(home_id, away_id):
    matches = get_h2h_matches(home_id, away_id, limit=6)
    h2h = H2HStats()
    session = Session()

    for match in matches:
        if match.home_goals is None:
            continue
        entry = {
            "home_id": match.home_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
        }
        home_stat = session.query(MatchStatistics).filter_by(
            match_id=match.api_id, team_id=match.home_team_id
        ).first()
        away_stat = session.query(MatchStatistics).filter_by(
            match_id=match.api_id, team_id=match.away_team_id
        ).first()
        if home_stat and away_stat:
            entry["total_corners"] = int((home_stat.corners or 0) + (away_stat.corners or 0))
            entry["total_cards"] = int(
                (home_stat.yellow_cards or 0) + (away_stat.yellow_cards or 0) +
                (home_stat.red_cards or 0) + (away_stat.red_cards or 0)
            )
        h2h.matches.append(entry)

    session.close()
    return h2h


async def get_todays_bet_options():
    session = Session()
    today = datetime.now().date()

    matches = session.query(Match).filter(
        Match.date >= datetime.combine(today, datetime.min.time()),
        Match.date < datetime.combine(today, datetime.max.time()),
        Match.status == "NS"
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
            ref = get_referee_stats(match.api_id)
            odds = fetch_odds(match.api_id)
            kick_off = match.date.strftime("%H:%M") if match.date else "?"

            options = get_all_markets(
                match_id=match.api_id,
                home=home_stats,
                away=away_stats,
                h2h=h2h,
                ref=ref,
                odds=odds,
                kick_off=kick_off,
                league=match.league_name,
            )
            all_options.extend(options)

        except Exception as e:
            print("match error: " + str(e))
            continue

    all_options.sort(key=lambda x: x.our_prob, reverse=True)
    print("options: " + str(len(all_options)))
    return all_options
