from dotenv import load_dotenv
import os

load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT"))
}

ADMIN_ID = int(os.getenv("ADMIN"))
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")