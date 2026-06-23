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
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_NAME = os.environ.get("OWNER_NAME", "Owner")

# Pulling individual API links from Vercel Secrets
API_URL_NUM = os.environ.get("API_URL_NUM")
API_URL_AADHAAR = os.environ.get("API_URL_AADHAAR")
API_URL_UPI = os.environ.get("API_URL_UPI")
API_URL_TG = os.environ.get("API_URL_TG")

# ==========================================
# FASTAPI & TELEGRAM SETUP
# ==========================================
app_fastapi = FastAPI()
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def filter_json_data(data: dict) -> str:
    """Removes unwanted metadata and formats the remaining data."""
    # Remove sensitive/unwanted API keys
    keys_to_remove = ["powered_by", "api_info", "developer", "credit"]
    for key in keys_to_remove:
        data.pop(key, None)
    
    # Format for Telegram
    output_lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            output_lines.append(f"<b>{html.escape(str(key).title())}:</b>")
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

async def handle_dynamic_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles multiple search commands and routes them to the correct API."""
    
    # 1. Determine which command was used (e.g., /num, /tg)
    command_used = update.message.text.split()[0].lower().split('@')[0]
    
    # 2. Map the command to the correct Vercel secret
    api_map = {
        "/num": API_URL_NUM,
        "/aadhar": API_URL_AADHAAR,
        "/upi": API_URL_UPI,
        "/tg": API_URL_TG
    }
    
    base_url = api_map.get(command_used)
    
    if not base_url:
        await update.message.reply_text("System Error: API mapping not found in environment.")
        return

    if not context.args:
        await update.message.reply_text(f"⚠️ Please provide a query. Example: {command_used} 12345")
        return
        
    query = quote(" ".join(context.args))
    
    # Construct the final URL (assuming the base URL ends with '=' as per your setup)
    final_url = f"{base_url}{query}"
    
    status_msg = await update.message.reply_text("Searching... Please wait ⏳")

    try:
        # 3. Make the async request
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(final_url)
            
            if resp.status_code == 200:
                raw_data = resp.json()
                clean_output = filter_json_data(raw_data)
                
                final_text = f"<b>Result for {html.escape(query)}:</b>\n\n{clean_output}"
                await status_msg.edit_text(final_text, parse_mode="HTML")
            else:
                await status_msg.edit_text(f"⚠️ External API Error. Code: {resp.status_code}")
                
    except Exception as e:
        await status_msg.edit_text("⚠️ A system error occurred while contacting the server.")

# ==========================================
# REGISTRATION & ROUTING
# ==========================================
bot_app.add_handler(CommandHandler("start", start))
# Register all search commands to the same dynamic handler
bot_app.add_handler(CommandHandler(["num", "aadhar", "upi", "tg"], handle_dynamic_search))

@app_fastapi.post("/webhook")
async def handle_webhook(request: Request):
    """Vercel entry point for Telegram POST requests."""
    if not bot_app._initialized:
        await bot_app.initialize()
        await bot_app.start()

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}
