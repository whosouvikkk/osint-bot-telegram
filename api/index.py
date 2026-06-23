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

# API Links from Vercel Secrets (ensure they end with '=')
API_URL_NUM = os.environ.get("API_URL_NUM")
API_URL_AADHAAR = os.environ.get("API_URL_AADHAAR")
API_URL_UPI = os.environ.get("API_URL_UPI")
API_URL_TG = os.environ.get("API_URL_TG")
API_URL_VEHICLE = os.environ.get("API_URL_VEHICLE")

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
    # This will completely drop the "powered_by" string and the entire "api_info" dictionary
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
    """A simple health check command."""
    await update.message.reply_text("Pong! 🌙 The server is active and responding.")

async def handle_dynamic_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles multiple search commands and routes them to the correct Vercel Secret API."""
    
    command_used = update.message.text.split()[0].lower().split('@')[0]
