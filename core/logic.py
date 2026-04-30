def analyze_goals(home, away, h2h):
    n = 5

    def avg_list(lst):
        return sum(lst[:n]) / max(len(lst[:n]), 1) if lst else 1.0

    home_scored = avg_list(home.goals_scored)
    home_conceded = avg_list(home.goals_conceded)
    away_scored = avg_list(away.goals_scored)
    away_conceded = avg_list(away.goals_conceded)

    h2h_list = [
        m["home_goals"] + m["away_goals"]
        for m in h2h.matches[:n]
        if "home_goals" in m
    ]
    h2h_avg = sum(h2h_list) / len(h2h_list) if h2h_list else (home_scored + away_scored)

    avg = (
        (home_scored + away_conceded) * 0.35 +
        (away_scored + home_conceded) * 0.35 +
        h2h_avg * 0.30
    )

    if avg >= 2.5:
        prob = min(0.82, 0.55 + (avg - 2.5) * 0.08)
        market = "Over 2.5 goli"
        odds_key = "over25"
    else:
        prob = min(0.82, 0.55 + (2.5 - avg) * 0.08)
        market = "Under 2.5 goli"
        odds_key = "under25"

    reason = (
        home.team_name + " sash: " + str(round(home_scored, 1)) +
        " | " + away.team_name + " sash: " + str(round(away_scored, 1)) +
        " | mosalodneli: " + str(round(avg, 2))
    )
    return {"market": market, "prob": prob, "reason": reason, "odds_key": odds_key}


# get_all_markets-ში goals ბლოკი გახდება:
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
        g = analyze_goals(home, away, h2h)
        results.append(make_option(
            g["market"], g["prob"],
            odds.get(g["odds_key"], 0),
            g["reason"]
        ))
    except Exception as e:
        print("goals error: " + str(e))

    try:
        r = analyze_1x2(home, away, h2h)
        results.append(make_option(r["home"]["market"], r["home"]["prob"], odds.get("home", 0), r["home"]["reason"]))
        results.append(make_option(r["draw"]["market"], r["draw"]["prob"], odds.get("draw", 0), r["draw"]["reason"]))
        results.append(make_option(r["away"]["market"], r["away"]["prob"], odds.get("away", 0), r["away"]["reason"]))
    except Exception as e:
        print("1x2 error: " + str(e))

    try:
        b = analyze_btts(home, away, h2h)
        odds_key = "btts_yes" if "diakh" in b["market"] else "btts_no"
        results.append(make_option(b["market"], b["prob"], odds.get(odds_key, 0), b["reason"]))
    except Exception as e:
        print("btts error: " + str(e))

    # corners და cards გამორთულია — ESPN მონაცემს არ იძლევა

    results = [r for r in results if r.our_prob >= 0.55]
    results.sort(key=lambda x: x.our_prob, reverse=True)
    return results
