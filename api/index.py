import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Retrieve environment variables (which you would set in Vercel Settings)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app_fastapi = FastAPI()

# 1. Define your commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running via Vercel Webhook! 🚀")

# 2. Build the Telegram Application (Done globally)
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))

# 3. Create the webhook endpoint
@app_fastapi.post("/webhook")
async def handle_webhook(request: Request):
    """
    This endpoint receives the POST requests from Telegram.
    """
    # Initialize the bot app if it hasn't been already
    if not bot_app._initialized:
        await bot_app.initialize()
        await bot_app.start()

    # Parse the incoming JSON into a Telegram Update object
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    
    # Process the update
    await bot_app.process_update(update)
    
    return {"status": "ok"}

@app_fastapi.get("/")
def home():
    return {"message": "Bot server is alive."}
