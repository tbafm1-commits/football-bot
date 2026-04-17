“””
bot/bot.py
Telegram ბოტი — მთავარი ფაილი
“””
import logging
from telegram import Update
from telegram.ext import (
Application, CommandHandler, ContextTypes, MessageHandler, filters
)
from dotenv import load_dotenv
import os

from core.accumulator import build_accumulator
from core.logic import get_all_markets
from bot.formatter import format_accumulator, format_no_acca
from sports.football.analyzer import get_todays_bet_options

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“⚽ *Football Betting Bot*\n\n”
“კომანდები:\n”
“/acca 5  — 5 კუში გენერაცია\n”
“/acca 10 — 10 კუში გენერაცია\n”
“/update  — მონაცემების განახლება\n\n”
“ან უბრალოდ მომწერე: *მინდა 7 კუში*”,
parse_mode=“Markdown”
)

async def acca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
“””
/acca 5  →  5 კუში
/acca 10 → 10 კუში
“””
try:
target = int(context.args[0]) if context.args else 5
except (ValueError, IndexError):
await update.message.reply_text(“გამოყენება: /acca 5”)
return

```
await _generate_acca(update, target)
```

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“””
მომხმარებელი წერს: “მინდა 7 კუში”
“””
text = update.message.text.lower()

```
if "კუში" in text or "კუშ" in text:
    # ვეძებთ რიცხვს
    import re
    numbers = re.findall(r'\d+', text)
    target = int(numbers[0]) if numbers else 5
    await _generate_acca(update, target)
else:
    await update.message.reply_text(
        "გამოყენება: მომწერე *მინდა 5 კუში*",
        parse_mode="Markdown"
    )
```

async def _generate_acca(update: Update, target: int):
“”“კუშის გენერაცია და გაგზავნა”””
msg = await update.message.reply_text(f”⏳ ვაგენერირებ {target} კუშს…”)

```
try:
    # ყველა მატჩის ყველა პოზიცია
    all_options = await get_todays_bet_options()

    if not all_options:
        await msg.edit_text("❌ დღეს მონაცემები არ არის. სცადე /update")
        return

    # კუშის გენერაცია
    acca = build_accumulator(all_options, target)

    if acca:
        text = format_accumulator(acca)
        await msg.edit_text(text, parse_mode="Markdown")
    else:
        await msg.edit_text(format_no_acca(target))

except Exception as e:
    logger.error(f"Acca error: {e}")
    await msg.edit_text(f"❌ შეცდომა: {e}")
```

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = await update.message.reply_text(“🔄 ვანახლებ…”)
from sports.football.fetcher import fetch_today_fixtures, fetch_all_standings
fetch_today_fixtures()
fetch_all_standings()
await msg.edit_text(“✅ განახლდა! სცადე /acca 5”)

def main():
from database.models import init_db
init_db()

```
app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("acca", acca_command))
app.add_handler(CommandHandler("update", update_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))

print("🤖 ბოტი გაშვებულია!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
