import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import os

from core.accumulator import build_accumulator
from bot.formatter import format_accumulator, format_no_acca
from sports.football.analyzer import get_todays_bet_options
from sports.football.fetcher import fetch_today_fixtures, fetch_all_standings
from database.models import init_db

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“Football Betting Bot\n\n”
“komandები:\n”
“/acca 5  - 5 კუში\n”
“/acca 10 - 10 კუში\n”
“/update  - განახლება\n\n”
“an momwere: minda 7 kushi”
)

async def acca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
target = int(context.args[0]) if context.args else 5
except (ValueError, IndexError):
await update.message.reply_text(“gamoyeneba: /acca 5”)
return
await _generate_acca(update, target)

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text.lower()
if “კუში” in text or “კუშ” in text:
numbers = re.findall(r’\d+’, text)
target = int(numbers[0]) if numbers else 5
await _generate_acca(update, target)
else:
await update.message.reply_text(“momwere: minda 5 kushi”)

async def _generate_acca(update: Update, target: int):
msg = await update.message.reply_text(“vagenerireb “ + str(target) + “ kushis…”)
try:
all_options = await get_todays_bet_options()
if not all_options:
await msg.edit_text(“dghes monacemebi ar aris. scade /update”)
return
acca = build_accumulator(all_options, target)
if acca:
text = format_accumulator(acca)
await msg.edit_text(text, parse_mode=“Markdown”)
else:
await msg.edit_text(format_no_acca(target))
except Exception as e:
logger.error(“Acca error: “ + str(e))
await msg.edit_text(“sheсdoma: “ + str(e))

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = await update.message.reply_text(“vanakhлeb…”)
fetch_today_fixtures()
fetch_all_standings()
await msg.edit_text(“ganakhlda! scade /acca 5”)

def main():
init_db()
app = Application.builder().token(os.getenv(“TELEGRAM_BOT_TOKEN”)).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CommandHandler(“acca”, acca_command))
app.add_handler(CommandHandler(“update”, update_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
print(“boti gaushvebula!”)
app.run_polling(drop_pending_updates=True)

if __name__ == “__main__”:
main()
