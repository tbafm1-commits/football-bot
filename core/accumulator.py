from itertools import combinations
from dataclasses import dataclass
from core.logic import BetOption
import math


ACCA_RANGES = {
    2:   (1.8,  2.2),
    3:   (2.5,  3.5),
    4:   (3.5,  4.5),
    5:   (4.0,  6.0),
    6:   (5.0,  7.0),
    7:   (6.0,  8.0),
    8:   (7.0,  9.5),
    10:  (9.0,  11.0),
    15:  (13.0, 17.0),
    20:  (18.0, 22.0),
    25:  (22.0, 28.0),
    30:  (27.0, 33.0),
    50:  (45.0, 55.0),
    100: (90.0, 110.0),
}


def get_range(target):
    if target in ACCA_RANGES:
        return ACCA_RANGES[target]
    return (target * 0.85, target * 1.15)


def ideal_legs(target, avg_odds):
    if avg_odds <= 1.0:
        return [4, 5]
    n = math.log(target) / math.log(avg_odds)
    n_floor = max(2, int(n))
    n_ceil = n_floor + 1
    return list(set([n_floor, n_ceil, n_floor + 2]))


def combo_score(legs):
    avg_prob = sum(l.our_prob for l in legs) / len(legs)
    return avg_prob


def total_odds(legs):
    result = 1.0
    for leg in legs:
        result *= leg.odds
    return round(result, 2)


def has_correlation(legs):
    match_markets = {}
    for leg in legs:
        mid = leg.match_id
        if mid not in match_markets:
            match_markets[mid] = []
        mtype = _market_type(leg.market)
        match_markets[mid].append(mtype)
    for mid, types in match_markets.items():
        if len(types) > 1:
            allowed = {"goals", "btts"}
            if not set(types).issubset(allowed):
                return True
            if len(types) > 2:
                return True
    return False


def _market_type(market):
    m = market.lower()
    if "over" in m or "under" in m:
        if "კუთხური" in m:
            return "corners"
        if "ბარათ" in m:
            return "cards"
        return "goals"
    if "btts" in m:
        return "btts"
    return "1x2"


@dataclass
class Accumulator:
    legs: list
    total_odds: float
    target: int
    avg_prob: float


def build_accumulator(all_options, target):
    low, high = get_range(target)
    if not all_options:
        return None

    avg_o = sum(o.odds for o in all_options) / len(all_options)
    leg_counts = ideal_legs(target, avg_o)

    best = None
    best_score = -1.0

    for n_legs in leg_counts:
        if n_legs > len(all_options):
            continue
        pool = all_options[:30]
        for combo in combinations(pool, n_legs):
            legs = list(combo)
            if has_correlation(legs):
                continue
            t_odds = total_odds(legs)
            if not (low <= t_odds <= high):
                continue
            score = combo_score(legs)
            if score > best_score:
                best_score = score
                best = legs

    if best is None:
        low2, high2 = target * 0.70, target * 1.30
        for n_legs in leg_counts:
            if n_legs > len(all_options):
                continue
            pool = all_options[:30]
            for combo in combinations(pool, n_legs):
                legs = list(combo)
                if has_correlation(legs):
                    continue
                t_odds = total_odds(legs)
                if not (low2 <= t_odds <= high2):
                    continue
                score = combo_score(legs)
                if score > best_score:
                    best_score = score
                    best = legs

    if best is None:
        return None

    avg_p = sum(l.our_prob for l in best) / len(best)
    return Accumulator(
        legs=best,
        total_odds=total_odds(best),
        target=target,
        avg_prob=round(avg_p, 3),
    )
