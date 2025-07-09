import os
from dotenv import load_dotenv

load_dotenv()

# Bot token
BOT_TOKEN = os.getenv('BOT_TOKEN', '7456835477:AAGDnPWLxOJn14Llk6qNOy5jY9PIUriD2Fw')

# Admin username
ADMIN_USERNAME = "@shamsiyev1909"

# Vaqt zonasi
TIMEZONE = "Asia/Tashkent"

# Database fayl
DATABASE_FILE = "bot_database.db" 