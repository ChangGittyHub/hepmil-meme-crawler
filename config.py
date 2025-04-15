import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Reddit API 
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# Paths
DB_PATH = "memes.db"
CHART_FILE = "chart.png"
LOG_FILE = "bot.log"

# PDF Settings
PDF_PAGE_SIZE = "letter"
MAX_MEMES_PER_DAY = 20
