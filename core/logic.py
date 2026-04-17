from dataclasses import dataclass, field
from typing import Optional


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
    games_played_home: int = 0
    games_played_away: int = 0
    home_results: list = field(default_factory=list)
    away_results: list = field(default_factory=list)
    rank: int = 10
    points: int = 0
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


def analyze_goals(home, away, h2h):
    n = 5
    home_total = sum(home.goals_scored[:n]) + sum(home.goals_conceded[:n])
    away_total = sum(away.goals_scored[:n]) + sum(away.goals_conceded[:n])
    h2h_list = [
        m["home_goals"] + m["away_goals"]
        for m in h2h.matches[:n]
        if "home_goals" in m
    ]
    h2h_total = sum(h2h_list)
    h2h_count = len(h2h_list)
    grand_total = home_total + away_total + h2h_total
    total_matches = n + n + h2h_count
    avg = grand_total / total_matches if total_matches > 0 else 2.5

    if avg < 2.0:
        market, prob = "Under 2.5 goli", 0.72
    elif avg < 2.8:
        market, prob = "Under 2.5 goli", 0.60
    elif avg < 3.4:
        market, prob = "Over 2.5 goli", 0.63
    elif avg < 4.2:
        market, prob = "Over 3.5 goli", 0.61
    else:
        market, prob = "Over 4.5 goli", 0.57

    reason = (
        home.team_name + " bolo 5: " + str(home_total) + " goli | " +
        away.team_name + " bolo 5: " + str(away_total) + " goli | " +
        "H2H " + str(h2h_count) + " match: " + str(h2h_total) + " goli | " +
        "sash: " + str(round(avg, 2))
    )
    return {"market": market, "prob": prob, "reason": reason, "avg": avg}


def _form_pts(results, n=5):
    pts = {"W": 3, "D": 1, "L": 0}
    total = sum(pts.get(r, 0) for r in results[:n])
    return total / (n * 3)


def analyze_1x2(home, away, h2h):
    home_form = _form_pts(home.home_results)
    away_form = _form_pts(away.away_results)
    pts_diff = (home.points - away.points) / max(home.played, 1)
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
        " | " + away.team_name + " " + str(round(away_form, 2)) +
        " | tablo: #" + str(home.rank) + " vs #" + str(away.rank) +
        " | H2H: " + str(h2h_hw) + "W " + str(h2h_d) + "D " + str(h2h_aw) + "L"
    )

    return {
        "home": {"market": home.team_name + " gamarjveba", "prob": round(hp, 3), "reason": reason},
        "draw": {"market": "fre", "prob": round(dp, 3), "reason": reason},
        "away": {"market": away.team_name + " gamarjveba", "prob": round(ap, 3), "reason": reason},
    }


def analyze_btts(home, away, h2h):
    n = 5
    home_scored_avg = sum(home.goals_scored[:n]) / n
    away_scored_avg = sum(away.goals_scored[:n]) / n
    home_cs_rate = home.clean_sheets_home / max(home.games_played_home, 1)
    away_cs_rate = away.clean_sheets_away / max(away.games_played_away, 1)

    h2h_btts = sum(
        1 for m in h2h.matches[:n]
        if m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0
    )
    h2h_btts_rate = h2h_btts / max(len(h2h.matches[:n]), 1)

    prob_home_scores = home_scored_avg / (home_scored_avg + 0.4) * (1 - away_cs_rate * 0.25)
    prob_away_scores = away_scored_avg / (away_scored_avg + 0.4) * (1 - home_cs_rate * 0.25)
    btts_prob = prob_home_scores * prob_away_scores * 0.55 + h2h_btts_rate * 0.45
    btts_prob = max(0.20, min(0.85, btts_prob))

    market = "BTTS - diakh" if btts_prob >= 0.52 else "BTTS - ara"
    final_prob = btts_prob if btts_prob >= 0.52 else 1 - btts_prob

    reason = (
        home.team_name + " sash.gatana: " + str(round(home_scored_avg, 1)) +
        " | " + away.team_name + " sash.gatana: " + str(round(away_scored_avg, 1)) +
        " | H2H BTTS: " + str(h2h_btts) + "/" + str(len(h2h.matches[:n]))
    )
    return {"market": market, "prob": round(final_prob, 3), "reason": reason}


def analyze_corners(home, away, h2h):
    n = 5
    home_c = sum(home.corners_for[:n]) + sum(home.corners_against[:n])
    away_c = sum(away.corners_for[:n]) + sum(away.corners_against[:n])
    h2h_c_list = [m["total_corners"] for m in h2h.matches[:n] if "total_corners" in m]
    h2h_c = sum(h2h_c_list)
    h2h_n = len(h2h_c_list)
    total = home_c + away_c + h2h_c
    matches = n + n + h2h_n
    avg = total / matches if matches > 0 else 9.5

    if avg < 8.0:
        market, prob = "Under 8.5 kutkhuri", 0.63
    elif avg < 9.5:
        market, prob = "Over 8.5 kutkhuri", 0.59
    elif avg < 11.0:
        market, prob = "Over 9.5 kutkhuri", 0.61
    else:
        market, prob = "Over 10.5 kutkhuri", 0.58

    reason = (
        home.team_name + " bolo 5 kutkhuri: " + str(home_c) +
        " | " + away.team_name + ": " + str(away_c) +
        " | sash: " + str(round(avg, 1))
    )
    return {"market": market, "prob": prob, "reason": reason, "avg": avg}


def analyze_cards(home, away, h2h, ref):
    n = 5
    home_y_avg = sum(home.yellow_cards[:n]) / n if home.yellow_cards else 1.8
    away_y_avg = sum(away.yellow_cards[:n]) / n if away.yellow_cards else 1.8
    h2h_c_list = [m["total_cards"] for m in h2h.matches[:n] if "total_cards" in m]
    h2h_cards_avg = sum(h2h_c_list) / len(h2h_c_list) if h2h_c_list else 3.5
    ref_factor = ref.avg_yellow_per_game / 4.0
    expected = (
        (home_y_avg + away_y_avg) * 0.35 +
        ref.avg_yellow_per_game * 0.40 +
        h2h_cards_avg * 0.25
    ) * ref_factor

    if expected < 2.5:
        market, prob = "Under 3.5 barati", 0.62
    elif expected < 3.5:
        market, prob = "Over 2.5 barati", 0.60
    elif expected < 4.5:
        market, prob = "Over 3.5 barati", 0.58
    else:
        market, prob = "Over 4.5 barati", 0.55

    reason = (
        "msaji [" + ref.name + "]: sash." + str(ref.avg_yellow_per_game) +
        " barati/thamashi | mosalodneli: " + str(round(expected, 1))
    )
    return {"market": market, "prob": prob, "reason": reason}


def analyze_penalties(home, away, ref):
    n = 5
    home_pen_avg = sum(home.penalties_conceded[:n]) / n if home.penalties_conceded else 0.25
    away_pen_avg = sum(away.penalties_conceded[:n]) / n if away.penalties_conceded else 0.25
    expected = (home_pen_avg + away_pen_avg) * 0.50 + ref.avg_penalties_per_game * 0.50

    if expected >= 0.45:
        market, prob = "1+ jarima", 0.58
    else:
        market, prob = "0 jarima", 0.60

    reason = (
        home.team_name + " jarima/thamashi: " + str(round(home_pen_avg, 2)) +
        " | " + away.team_name + ": " + str(round(away_pen_avg, 2)) +
        " | msaji: " + str(ref.avg_penalties_per_game)
    )
    return {"market": market, "prob": prob, "reason": reason}


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

    g = analyze_goals(home, away, h2h)
    if "Over" in g["market"]:
        results.append(make_option(g["market"], g["prob"], odds.get("over25", 0), g["reason"]))
    else:
        results.append(make_option(g["market"], g["prob"], odds.get("under25", 0), g["reason"]))

    r = analyze_1x2(home, away, h2h)
    results.append(make_option(r["home"]["market"], r["home"]["prob"], odds.get("home", 0), r["home"]["reason"]))
    results.append(make_option(r["draw"]["market"], r["draw"]["prob"], odds.get("draw", 0), r["draw"]["reason"]))
    results.append(make_option(r["away"]["market"], r["away"]["prob"], odds.get("away", 0), r["away"]["reason"]))

    b = analyze_btts(home, away, h2h)
    odds_key = "btts_yes" if "diakh" in b["market"] else "btts_no"
    results.append(make_option(b["market"], b["prob"], odds.get(odds_key, 0), b["reason"]))

    c = analyze_corners(home, away, h2h)
    c_key = "over95c" if "9.5" in c["market"] else "over85c"
    results.append(make_option(c["market"], c["prob"], odds.get(c_key, 0), c["reason"]))

    cards = analyze_cards(home, away, h2h, ref)
    cards_key = "over35cards" if "3.5" in cards["market"] else "over25cards"
    results.append(make_option(cards["market"], cards["prob"], odds.get(cards_key, 0), cards["reason"]))

    pen = analyze_penalties(home, away, ref)
    results.append(make_option(pen["market"], pen["prob"], odds.get("pen_yes", 0), pen["reason"]))

    results = [r for r in results if r.odds >= 1.25 and r.our_prob >= 0.55]
    results.sort(key=lambda x: x.our_prob, reverse=True)
    return results
