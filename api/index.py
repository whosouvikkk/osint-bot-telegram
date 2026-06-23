import os
import html
import httpx
import logging
import certifi
from urllib.parse import quote
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.constants import ChatMemberStatus
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# 1. FASTAPI INITIALIZATION
# ==========================================
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
raw_channel = os.environ.get("CHANNEL_LINK", "").strip()
OWNER_NAME = os.environ.get("OWNER_NAME", "Owner").strip()
try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0").strip())
except ValueError:
    ADMIN_ID = 0

# Auto-format channel link
if "t.me/" in raw_channel:
    CHANNEL_LINK = "@" + raw_channel.split("t.me/")[-1].split("/")[0]
else:
    CHANNEL_LINK = raw_channel

# Safe Lazy Initialization
bot = None
users_col = None
whitelist_col = None

def init_services():
    global bot, users_col, whitelist_col
    if bot is None:
        bot = Bot(token=BOT_TOKEN)
        client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
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

# ==========================================
# HELPER FUNCTIONS
# ==========================================
async def check_membership(user_id: int) -> bool:
    """Checks if the user is in the required Telegram channel."""
    if not CHANNEL_LINK: 
        return True
    try:
        if user_id == ADMIN_ID:
            return True
            
        member = await bot.get_chat_member(CHANNEL_LINK, user_id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            return False
        return True
    except Exception as e:
        logger.error(f"MEMBERSHIP CRASH for channel '{CHANNEL_LINK}': {e}")
        return False

def filter_data(data: dict) -> str:
    """Formats JSON data line-by-line, properly unpacking nested dictionaries inside lists."""
    for k in ["powered_by", "api_info", "developer", "credit", "status", "success"]: 
        data.pop(k, None)
        
    lines = []
    for k, v in data.items():
        clean_key = html.escape(str(k).replace('_', ' ').replace('-', ' ').title())
        
        if isinstance(v, dict):
            lines.append(f"🔷 <b>{clean_key}:</b>")
            for sk, sv in v.items(): 
                clean_sub_key = html.escape(str(sk).replace('_', ' ').replace('-', ' ').title())
                lines.append(f"   • <b>{clean_sub_key}:</b> {html.escape(str(sv))}")
                
        elif isinstance(v, list):
            lines.append(f"🔷 <b>{clean_key}:</b>")
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    lines.append(f"\n   🔸 <b>Record {i+1}:</b>")
                    for sk, sv in item.items():
                        clean_sub_key = html.escape(str(sk).replace('_', ' ').replace('-', ' ').title())
                        lines.append(f"      ▪️ <b>{clean_sub_key}:</b> {html.escape(str(sv))}")
                else:
                    lines.append(f"   • {html.escape(str(item))}")
        else: 
            lines.append(f"• <b>{clean_key}:</b> {html.escape(str(v))}")
            
    lines.append(f"\n👤 <b>Developer:</b> {OWNER_NAME}")
    return "\n".join(lines)

# ==========================================
# MESSAGE ROUTER
# ==========================================
async def process_message(update: Update):
    if not update.message or not update.message.text: return
    
    text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    
    parts = text.split()
    cmd = parts[0].lower().split('@')[0]
    args = parts[1:]
    
    # --- COMMAND: /start ---
    if cmd == "/start":
        msg = (
            "👻 <b>MoonWitch OSINT</b>\n\n"
            "<b>Commands:</b>\n"
            "• <code>/num &lt;number&gt;</code> - Number lookup\n"
            "• <code>/aadhar &lt;number&gt;</code> - Aadhar lookup\n"
            "• <code>/upi &lt;id&gt;</code> - UPI lookup\n"
            "• <code>/tg &lt;user&gt;</code> - Telegram trace\n"
            "• <code>/vehicle &lt;number&gt;</code> - Vehicle info\n"
            "• <code>/credits</code> - Check users credits\n"
            "• <code>/buycredits</code> - Buy credits info\n"
            "• <code>/whitelist &lt;input&gt;</code> - Protect info\n"
            "• <code>/price</code> - View pricing\n"
            "• <code>/donate</code> - Support us"
        )
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        
    # --- COMMAND: /credits ---
    elif cmd == "/credits":
        user = await users_col.find_one({"_id": user_id_str})
        credits = user.get("credits", 4) if user else 4
        await bot.send_message(chat_id=chat_id, text=f"💳 Your credits: <b>{credits}</b>", parse_mode="HTML")
        
    # --- COMMAND: /buycredits ---
    elif cmd == "/buycredits":
        await bot.send_message(chat_id=chat_id, text=f"1 Credits - 2rs -  Each search || Contact {OWNER_NAME} for buying credits")
        
    # --- COMMAND: /price ---
    elif cmd == "/price":
        await bot.send_message(chat_id=chat_id, text=f"Custom Bot with Unlimited Credits - 499rs\n Permanent Api Key - 1999rs  {OWNERNAME} ")
        
    # --- COMMAND: /whitelist ---
    elif cmd == "/whitelist":
        await bot.send_message(chat_id=chat_id, text=f"For whitelisting ur infos contact owner {OWNER_NAME}")
        
    # --- COMMAND: /donate ---
    elif cmd == "/donate":
        try:
            with open("qr.png", "rb") as qr_file:
                await bot.send_photo(chat_id=chat_id, photo=qr_file, caption="Donate and get a secret surprise gift from us..!! Contact - @souvik_halla ")
        except FileNotFoundError:
            await bot.send_message(chat_id=chat_id, text="⚠️ <b>Error:</b> qr.png not found in server.", parse_mode="HTML")
            
    # --- COMMAND: /add (ADMIN ONLY) ---
    elif cmd == "/add":
        if user_id == ADMIN_ID:
            if len(args) == 2:
                try:
                    target_id = args[0]
                    amount = int(args[1])
                    await users_col.update_one(
                        {"_id": target_id}, 
                        {"$inc": {"credits": amount}}, 
                        upsert=True
                    )
                    await bot.send_message(chat_id=chat_id, text=f"✅ Added {amount} credits to user {target_id}.")
                except ValueError:
                    await bot.send_message(chat_id=chat_id, text="⚠️ Amount must be a number.")
            else:
                await bot.send_message(chat_id=chat_id, text="Usage: /add <tg_id> <amount>")
        else:
            await bot.send_message(chat_id=chat_id, text="⛔ You do not have permission to use this command.")

    # --- COMMAND: /stats (ADMIN ONLY) ---
    elif cmd == "/stats":
        if user_id == ADMIN_ID:
            try:
                # Fetch up to 100 users to prevent exceeding Telegram's message limits
                users_cursor = users_col.find({})
                users_list = await users_cursor.to_list(length=100)
                total_users = await users_col.count_documents({})
                
                if not users_list:
                    await bot.send_message(chat_id=chat_id, text="📊 No users found in database.")
                    return
                    
                lines = [f"📊 <b>Bot Statistics</b>", f"👥 Total Users: <b>{total_users}</b>\n"]
                for u in users_list:
                    user_id_display = u.get('_id', 'Unknown')
                    user_credits = u.get('credits', 0)
                    lines.append(f"👤 <code>{user_id_display}</code> - Credits: {user_credits}")
                    
                if total_users > 100:
                    lines.append("\n<i>...Showing first 100 users</i>")
                    
                stats_text = "\n".join(lines)
                
                # Failsafe for telegram character limits
                if len(stats_text) > 4000:
                    stats_text = stats_text[:4000] + "\n...[Truncated]"
                    
                await bot.send_message(chat_id=chat_id, text=stats_text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Stats API Error: {e}")
                await bot.send_message(chat_id=chat_id, text="⚠️ Error retrieving stats.")
        else:
            await bot.send_message(chat_id=chat_id, text="⛔ You do not have permission to use this command.")
            
    # --- SEARCH COMMANDS ---
    elif cmd in ["/num", "/aadhar", "/upi", "/tg", "/vehicle"]:
        if not await check_membership(user_id):
            await bot.send_message(chat_id=chat_id, text=f"⚠️ Join our channel to use this bot: {raw_channel}")
            return
            
        user = await users_col.find_one({"_id": user_id_str})
        credits = user.get("credits", 4) if user else 4
        if credits <= 0:
            await bot.send_message(chat_id=chat_id, text="❌ No credits. Contact /buycredits.")
            return
            
        if not args:
            await bot.send_message(chat_id=chat_id, text=f"⚠️ Please provide a value. Example: {cmd} query")
            return
        query = " ".join(args)
        
        if query.lower() in ["7980346028", "souvik_halla", "meow"] or await whitelist_col.find_one({"val": query}):
            await bot.send_message(chat_id=chat_id, text="🛡️ Protected")
            return
            
        api_url = API_MAP.get(cmd)
        if not api_url:
            await bot.send_message(chat_id=chat_id, text="⚠️ System Error: API URL not configured for this command.")
            return
            
        status_msg = await bot.send_message(chat_id=chat_id, text="Searching the shadows... ⏳")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as http_client:
                resp = await http_client.get(f"{api_url}{quote(query)}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    formatted_text = filter_data(data)
                    
                    await users_col.update_one({"_id": user_id_str}, {"$set": {"credits": credits - 1}}, upsert=True)
                    await bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=formatted_text, parse_mode="HTML")
                else:
                    await bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"⚠️ API Error: Code {resp.status_code}")
        except Exception as e:
            logger.error(f"Search API Error: {e}")
            safe_error = html.escape(str(e))
            await bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=f"⚠️ <b>System Error:</b>\n<code>{safe_error}</code>", parse_mode="HTML")

# ==========================================
# UNIVERSAL WEBHOOK ROUTE
# ==========================================
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def handle_webhook(request: Request):
    if request.method == "GET":
        return {"status": "active", "message": "Bot is listening!"}
    
    try:
        init_services()
        body = await request.json()
        update = Update.de_json(body, bot)
        await process_message(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Critical Webhook Error: {e}", exc_info=True)
        return {"status": "error"}
