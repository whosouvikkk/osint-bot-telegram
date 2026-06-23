import os
import html
import httpx
import logging
from urllib.parse import quote
from fastapi import FastAPI, Request
from telegram import Update, Bot
from motor.motor_asyncio import AsyncIOMotorClient

# Setup Logging to see errors in Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "").strip()
OWNER_NAME = os.environ.get("OWNER_NAME", "Owner").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0").strip())

# DB & Bot
client = AsyncIOMotorClient(MONGO_URI)
db = client.osint_bot_db
users_col = db.users
whitelist_col = db.whitelist
bot = Bot(token=BOT_TOKEN)

app = FastAPI()

# --- Logic ---
async def process_message(update: Update):
    if not update.message or not update.message.text: return
    
    text = update.message.text
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    
    # Simple Router
    if text.startswith("/start"):
        await bot.send_message(chat_id=chat_id, text="👻 <b>MoonWitch OSINT</b>\nCommands: /num, /upi, /tg, /vehicle, /credits", parse_mode="HTML")
    
    elif text.startswith(("/num", "/upi", "/tg", "/vehicle", "/aadhar")):
        # Basic Credit/Member Check Logic
        user = await users_col.find_one({"_id": user_id})
        credits = user.get("credits", 4) if user else 4
        
        if credits <= 0:
            await bot.send_message(chat_id=chat_id, text="❌ No credits. Contact /buycredits.")
            return
            
        await bot.send_message(chat_id=chat_id, text=f"🔍 Searching... (Remaining: {credits})")
        await users_col.update_one({"_id": user_id}, {"$set": {"credits": credits - 1}}, upsert=True)

    elif text.startswith("/credits"):
        user = await users_col.find_one({"_id": user_id})
        bal = user.get("credits", 4) if user else 4
        await bot.send_message(chat_id=chat_id, text=f"💳 Your balance: {bal}")

# --- Webhook ---
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def handle_webhook(request: Request):
    if request.method == "GET":
        return {"status": "active"}
    
    try:
        body = await request.json()
        update = Update.de_json(body, bot)
        await process_message(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"status": "error"}
