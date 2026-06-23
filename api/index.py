import os
import html
import httpx
from urllib.parse import quote
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ChatMemberStatus
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# ENVIRONMENT & DATABASE
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "").strip()
OWNER_NAME = os.environ.get("OWNER_NAME", "Owner").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0").strip())

client = AsyncIOMotorClient(MONGO_URI)
db = client.osint_bot_db
users_col = db.users
whitelist_col = db.whitelist

API_MAP = {
    "/num": os.environ.get("API_URL_NUM", "").strip(),
    "/aadhar": os.environ.get("API_URL_AADHAAR", "").strip(),
    "/upi": os.environ.get("API_URL_UPI", "").strip(),
    "/tg": os.environ.get("API_URL_TG", "").strip(),
    "/vehicle": os.environ.get("API_URL_VEHICLE", "").strip()
}

app = FastAPI()
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ==========================================
# HELPERS
# ==========================================
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_LINK: return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_LINK, update.effective_user.id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await update.message.reply_text(f"⚠️ Join our channel to use this bot: {CHANNEL_LINK}")
            return False
        return True
    except: return False

def filter_data(data: dict) -> str:
    for k in ["powered_by", "api_info", "developer", "credit"]: data.pop(k, None)
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"\n<b>{html.escape(k.replace('_', ' ').title())}:</b>")
            for sk, sv in v.items(): lines.append(f"  • {html.escape(sk.title())}: {html.escape(str(sv))}")
        else: lines.append(f"<b>{html.escape(k.replace('_', ' ').title())}:</b> {html.escape(str(v))}")
    lines.append(f"\n<b>Developer:</b> {OWNER_NAME}")
    return "\n".join(lines)

# ==========================================
# COMMANDS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = ("👻 <b>MoonWitch OSINT</b>\n\n"
           "/num <num> : Number lookup\n"
           "/upi <upi> : UPI lookup\n"
           "/tg <user> : Telegram trace\n"
           "/vehicle <num> : Vehicle info\n"
           "/credits : Check balance\n"
           "/buycredits : Buy info\n"
           "/whitelist : Protect info\n"
           "/price : View pricing\n"
           "/donate : Support us")
    await update.message.reply_text(msg, parse_mode="HTML")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_membership(update, context): return
    uid = str(update.effective_user.id)
    
    user = await users_col.find_one({"_id": uid})
    credits = user.get("credits", 4) if user else 4
    if credits <= 0:
        await update.message.reply_text("❌ No credits. Contact /buycredits.")
        return

    cmd = update.message.text.split()[0].lower().split('@')[0]
    query = " ".join(context.args)
    
    if query in ["7980346028", "souvik_halla", "kadu3"] or await whitelist_col.find_one({"val": query}):
        await update.message.reply_text("🛡️ Protected")
        return

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{API_MAP[cmd]}{quote(query)}")
            if resp.status_code == 200:
                await users_col.update_one({"_id": uid}, {"$set": {"credits": credits - 1}}, upsert=True)
                await update.message.reply_text(filter_data(resp.json()), parse_mode="HTML")
            else: await update.message.reply_text("⚠️ API Error.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {html.escape(str(e))}", parse_mode="HTML")

# Registration
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler(["num", "aadhar", "upi", "tg", "vehicle"], handle_search))
bot_app.add_handler(CommandHandler("credits", lambda u, c: u.message.reply_text(f"Your credits: {users_col.find_one({'_id': str(u.effective_user.id)}).get('credits', 4) if users_col.find_one({'_id': str(u.effective_user.id)}) else 4}")))
bot_app.add_handler(CommandHandler("buycredits", lambda u, c: u.message.reply_text(f"Contact {OWNER_NAME}. 2rs/credit.")))
bot_app.add_handler(CommandHandler("price", lambda u, c: u.message.reply_text(f"kaddu lele {ADMIN_ID}")))
bot_app.add_handler(CommandHandler("whitelist", lambda u, c: u.message.reply_text(f"To whitelist info, contact {OWNER_NAME}")))
bot_app.add_handler(CommandHandler("donate", lambda u, c: u.message.reply_photo(open("qr.png", "rb"), caption="kadddu lele")))
bot_app.add_handler(CommandHandler("add", lambda u, c: users_col.update_one({"_id": c.args[0]}, {"$inc": {"credits": int(c.args[1])}}, upsert=True) if u.effective_user.id == ADMIN_ID else None))

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    await bot_app.process_update(Update.de_json(data, bot_app.bot))
    return {"status": "ok"}
