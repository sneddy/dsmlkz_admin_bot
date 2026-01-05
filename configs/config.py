import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ROLE_KEY")
SUPABASE_BUCKET = "telegram-images"
FACES_BUCKET = "faces"
USER_ID = 212657982
HR_ASSISTANT_MODEL = os.getenv("HR_ASSISTANT_MODEL", "gpt-4o-mini")
