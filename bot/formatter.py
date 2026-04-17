“””
bot/formatter.py
Telegram-ისთვის ლამაზი გამომავალი ფორმატი
“””
from core.accumulator import Accumulator
from core.logic import BetOption

def format_accumulator(acca: Accumulator) -> str:
“”“კუშის ფორმატირება Telegram-ისთვის”””

```
lines = []
lines.append(f"🎯 *{acca.target} კუში*")
lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")

for i, leg in enumerate(acca.legs, 1):
    prob_bar = _prob_bar(leg.our_prob)
    lines.append(f"\n*{i}.* {leg.home_team} vs {leg.away_team}")
    lines.append(f"    🏆 {leg.league} | 🕐 {leg.kick_off}")
    lines.append(f"    ✅ *{leg.market}*")
    lines.append(f"    📊 {leg.reason}")
    lines.append(f"    {prob_bar} {leg.our_prob*100:.0f}%")
    lines.append(f"    💰 კოეფ: *{leg.odds}*")

lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
lines.append(f"🏆 *ჯამური კოეფიციენტი: {acca.total_odds}*")
lines.append(f"📈 საშ. სანდოობა: {acca.avg_prob*100:.0f}%")
lines.append(f"📌 პოზიციები: {len(acca.legs)}")
lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
lines.append(f"⚠️ _სტატისტიკური ანალიზია, არა გარანტია_")

return "\n".join(lines)
```

def format_no_acca(target: int) -> str:
return (
f”❌ *{target} კუში ვერ შეიქმნა*\n\n”
f”მიზეზი: დღეს საკმარისი მატჩი არ არის “
f”ან კოეფიციენტები {target}-ის დიაპაზონში არ ხვდება.\n\n”
f”სცადე: /acca 5 ან /acca 10”
)

def _prob_bar(prob: float) -> str:
filled = int(prob * 10)
return “█” * filled + “░” * (10 - filled)
