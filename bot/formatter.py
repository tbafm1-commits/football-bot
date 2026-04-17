from core.accumulator import Accumulator
from core.logic import BetOption


def format_accumulator(acca):
    lines = []
    lines.append("*" + str(acca.target) + " kushi*")
    lines.append("=" * 22)

    for i, leg in enumerate(acca.legs, 1):
        prob_bar = _prob_bar(leg.our_prob)
        lines.append("")
        lines.append(str(i) + ". " + leg.home_team + " vs " + leg.away_team)
        lines.append("   " + leg.league + " | " + leg.kick_off)
        lines.append("   *" + leg.market + "*")
        lines.append("   " + leg.reason)
        lines.append("   " + prob_bar + " " + str(round(leg.our_prob * 100)) + "%")
        lines.append("   koef: *" + str(leg.odds) + "*")

    lines.append("")
    lines.append("=" * 22)
    lines.append("*jamuri koeficienti: " + str(acca.total_odds) + "*")
    lines.append("sash. sandooba: " + str(round(acca.avg_prob * 100)) + "%")
    lines.append("poziciebi: " + str(len(acca.legs)))

    return "\n".join(lines)


def format_no_acca(target):
    return (
        str(target) + " kushi ver sheiqmna.\n\n"
        "dghes sakmarisi match ar aris.\n"
        "scade: /acca 5 an /acca 10"
    )


def _prob_bar(prob):
    filled = int(prob * 10)
    return "█" * filled + "░" * (10 - filled)
