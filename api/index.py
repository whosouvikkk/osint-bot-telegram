import os
import html
import httpx
from urllib.parse import quote
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==========================================
# VERCEL ENVIRONMENT VARIABLES (SECRETS)
# ==========================================
# ==========================================
# VERCEL ENVIRONMENT VARIABLES (SECRETS)
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# API Links from Vercel Secrets 
# Adding .strip() removes any accidental invisible spaces or newlines from Vercel
API_URL_NUM = os.environ.get("API_URL_NUM", "").strip()
API_URL_AADHAAR = os.environ.get("API_URL_AADHAAR", "").strip()
API_URL_UPI = os.environ.get("API_URL_UPI", "").strip()
API_URL_TG = os.environ.get("API_URL_TG", "").strip()
API_URL_VEHICLE = os.environ.get("API_URL_VEHICLE", "").strip()

# ==========================================
# FASTAPI & TELEGRAM SETUP
# ==========================================
app = FastAPI() 
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def filter_json_data(data: dict) -> str:
    """Removes unwanted metadata and formats the remaining data."""
    keys_to_remove = ["powered_by", "api_info", "developer", "credit"]
    for key in keys_to_remove:
        data.pop(key, None)
    
    output_lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            output_lines.append(f"\n<b>{html.escape(str(key).replace('_', ' ').title())}:</b>")
            for sub_k, sub_v in value.items():
                output_lines.append(f"  • {html.escape(str(sub_k).title())}: {html.escape(str(sub_v))}")
        else:
            formatted_key = html.escape(str(key).replace("_", " ").title())
            output_lines.append(f"<b>{formatted_key}:</b> {html.escape(str(value))}")
            
    return "\n".join(output_lines)

# ==========================================
# COMMAND HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("System Online. Webhook active. 🚀")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! 🌙 The server is active and responding.")

async def handle_dynamic_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles multiple search commands and routes them to the correct Vercel Secret API."""
    command_used = update.message.text.split()[0].lower().split('@')[0]
    
    api_map = {
        "/num": API_URL_NUM,
        "/aadhar": API_URL_AADHAAR,
        "/upi": API_URL_UPI,
        "/tg": API_URL_TG,
        "/vehicle": API_URL_VEHICLE 
    }
    
    base_url = api_map.get(command_used)
    
    if not base_url:
        await update.message.reply_text("⚠️ System Error: API mapping not found in Vercel environment variables.")
        return

    if not context.args:
        await update.message.reply_text(f"⚠️ Please provide a query. Example: {command_used} 12345")
        return
        
    query = quote(" ".join(context.args))
    final_url = f"{base_url}{query}"
    
    status_msg = await update.message.reply_text("Searching the shadows... Please wait ⏳")

    try:
        # Increased timeout to 60 seconds to handle Render server cold starts
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(final_url)
            
            if resp.status_code == 200:
                raw_data = resp.json()
                clean_output = filter_json_data(raw_data)
                
                final_text = f"<b>Result for {html.escape(query)}:</b>\n\n{clean_output}"
                await status_msg.edit_text(final_text, parse_mode="HTML")
            else:
                await status_msg.edit_text(f"⚠️ External API Error. Code: {resp.status_code}")
                
    except Exception as e:
        # Detailed error exposure for debugging
        safe_error = html.escape(str(e))
        await status_msg.edit_text(f"⚠️ <b>System Error Encountered:</b>\n<code>{safe_error}</code>", parse_mode="HTML")

# ==========================================
# REGISTRATION & ROUTING
# ==========================================
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("ping", ping))
bot_app.add_handler(CommandHandler(["num", "aadhar", "upi", "tg", "vehicle"], handle_dynamic_search))

# Catch the webhook request on EVERY possible path combination Vercel might use
@app.post("/")
@app.post("/webhook")
@app.post("/api")
@app.post("/api/index")
@app.post("/api/webhook")
async def handle_webhook(request: Request):
    """Universal webhook endpoint that processes updates from Telegram."""
    if not bot_app._initialized:
        await bot_app.initialize()
        await bot_app.start()

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

# Catch browser visits on any of these paths to display the status message
@app.get("/")
@app.get("/api")
@app.get("/api/index")
def home():
    """Health check endpoint to verify the server is running."""
    return {"message": "Telegram Bot Webhook Server is active and listening! 🚀"}
