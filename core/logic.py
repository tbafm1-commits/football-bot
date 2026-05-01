from dataclasses import dataclass, field


@dataclass
class TeamStats:
    team_id: int
    team_name: str
    is_home: bool
    goals_scored: list = field(default_factory=list)
    goals_conceded: list = field(default_factory=list)
    home_goals_scored: list = field(default_factory=list)
    home_goals_conceded: list = field(default_factory=list)
    away_goals_scored: list = field(default_factory=list)
    away_goals_conceded: list = field(default_factory=list)
    corners_for: list = field(default_factory=list)
    corners_against: list = field(default_factory=list)
    yellow_cards: list = field(default_factory=list)
    red_cards: list = field(default_factory=list)
    fouls_committed: list = field(default_factory=list)
    penalties_conceded: list = field(default_factory=list)
    clean_sheets_home: int = 0
    clean_sheets_away: int = 0
    games_played_home: int = 1
    games_played_away: int = 1
    home_results: list = field(default_factory=list)
    away_results: list = field(default_factory=list)
    rank: int = 10
    points: int = 20
    played: int = 1


@dataclass
class H2HStats:
    matches: list = field(default_factory=list)


@dataclass
class RefereeStats:
    name: str = "Unknown"
    avg_yellow_per_game: float = 4.0
    avg_red_per_game: float = 0.2
    avg_fouls_per_game: float = 22.0
    avg_penalties_per_game: float = 0.3


@dataclass
class BetOption:
    match_id: int
    home_team: str
    away_team: str
    league: str
    kick_off: str
    market: str
    our_prob: float
    odds: float
    reason: str


def s(lst, n=5, default=1):
    if not lst:
        return [default] * n
    return lst[:n] if len(lst) >= n else lst + [default] * (n - len(lst))


def _form_pts(results, n=5):
    pts = {"W": 3, "D": 1, "L": 0}
    r = s(results, n, "D")
    return sum(pts.get(x, 1) for x in r) / (n * 3)


def analyze_1x2(home, away, h2h):
    home_form  = _form_pts(home.home_results)
    away_form  = _form_pts(away.away_results)
    pts_diff   = (home.points - away.points) / max(home.played, 1)
    rank_factor = (away.rank - home.rank) / 20

    n = 5
    h2h_hw = sum(
        1 for m in h2h.matches[:n]
        if m.get("home_id") == home.team_id
        and m.get("home_goals", 0) > m.get("away_goals", 0)
    )
    h2h_aw = sum(
        1 for m in h2h.matches[:n]
        if m.get("home_id") == home.team_id
        and m.get("away_goals", 0) > m.get("home_goals", 0)
    )
    h2h_d = len(h2h.matches[:n]) - h2h_hw - h2h_aw
    h2h_n = max(len(h2h.matches[:n]), 1)

    home_str = (
        home_form * 0.35 +
        max(0, pts_diff * 0.10) +
        max(0, rank_factor * 0.15) +
        (h2h_hw / h2h_n) * 0.20 +
        0.10
    )
    away_str = (
        away_form * 0.35 +
        max(0, -pts_diff * 0.10) +
        max(0, -rank_factor * 0.15) +
        (h2h_aw / h2h_n) * 0.20
    )
    draw_str = 0.25 + (h2h_d / h2h_n) * 0.10

    total = home_str + away_str + draw_str
    hp = home_str / total
    dp = draw_str / total
    ap = away_str / total

    reason = (
        "forma: " + home.team_name + " " + str(round(home_form, 2)) +
        " vs " + away.team_name + " " + str(round(away_form, 2)) +
        " | H2H: " + str(h2h_hw) + "W " + str(h2h_d) + "D " + str(h2h_aw) + "L"
    )

    return {
        "home": {"market": home.team_name + " gamarjveba", "prob": round(hp, 3), "reason": reason},
        "draw": {"market": "fre", "prob": round(dp, 3), "reason": reason},
        "away": {"market": away.team_name + " gamarjveba", "prob": round(ap, 3), "reason": reason},
    }


def get_all_markets(match_id, home, away, h2h, ref, odds, kick_off, league):
    results = []

    def make_option(market, prob, odds_val, reason):
        return BetOption(
            match_id=match_id,
            home_team=home.team_name,
            away_team=away.team_name,
            league=league,
            kick_off=kick_off,
            market=market,
            our_prob=prob,
            odds=odds_val,
            reason=reason,
        )

    try:
        r = analyze_1x2(home, away, h2h)
        results.append(make_option(r["home"]["market"], r["home"]["prob"], odds.get("home", 0), r["home"]["reason"]))
        results.append(make_option(r["draw"]["market"], r["draw"]["prob"], odds.get("draw", 0), r["draw"]["reason"]))
        results.append(make_option(r["away"]["market"], r["away"]["prob"], odds.get("away", 0), r["away"]["reason"]))
    except Exception as e:
        print("1x2 error: " + str(e))

    results = [r for r in results if r.our_prob >= 0.55]
    results.sort(key=lambda x: x.our_prob, reverse=True)
    return results
