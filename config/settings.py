import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ALLOWED_USERS = [
    int(os.getenv('USER_ID_1', '0')),
    int(os.getenv('USER_ID_2', '0'))
]

# GitHub
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', '')

# Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# App
PORT = int(os.getenv('PORT', 8080))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Tu URL de render.com
