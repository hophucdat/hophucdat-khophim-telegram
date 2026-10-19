import os
from dotenv import load_dotenv

load_dotenv()

HOME_BOT_TOKEN = os.getenv("HOME_BOT_TOKEN")
STREAM_BOT_TOKEN = os.getenv("STREAM_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ADMIN_IDS = [int(aid.strip()) for aid in os.getenv("ADMIN_IDS", "").split(",") if aid.strip()]