import pathlib
import os
import discord
from logging.config import dictConfig
from dotenv import load_dotenv
import sqlite3

# Ensure the logs directory exists before configuring logging
BASE_DIR = pathlib.Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR = BASE_DIR / "data"

# Parse env
load_dotenv()

# Bot Token
DISCORD_API_SECRET = os.getenv("DISCORD_API_SECRET")

# Base Config
BASE_SERVER_ID = discord.Object(id=int(os.getenv("BASE_SERVER_ID", 0)))
BASE_OWNER_ID = int(os.getenv("BASE_OWNER_ID", 0))
All_COMMANDS_REQUIRED_ROLE_ID = int(os.getenv("All_COMMANDS_REQUIRED_ROLE_ID", 0))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
CHANNEL_NOTIFIER_ID = int(os.getenv("CHANNEL_NOTIFIER_ID", 0))
NOTIFICATION_ROLE = int(os.getenv("NOTIFICATION_ROLE", 0))
TIME_INTERVAL_TO_DOWNLOAD = int(os.getenv("TIME_INTERVAL_TO_DOWNLOAD", 60))
TIME_INTERVAL_TO_MESSAGE = int(os.getenv("TIME_INTERVAL_TO_MESSAGE", 10))
TIME_INTERVAL = int(os.getenv("TIME_INTERVAL", 60))
BASE_DIRECTORY = os.getenv("BASE_DIRECTORY", "data")
FETCH_DIRECTLY = os.getenv("FETCH_DIRECTLY", "false").lower() == "true"
LOG_ONLY_NEW_VERSIONS = os.getenv("LOG_ONLY_NEW_VERSIONS", "true").lower() == "true"

# Path settings
BASE_PATH = pathlib.Path(BASE_DIRECTORY).absolute()
STORAGE_DIRECTORY = BASE_PATH / "stored"
DOWNLOAD_DIRECTORY = BASE_PATH / "download"
STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

# SQLite settings
DATABASE_PATH = BASE_PATH / "patchdatabase_v2.db"
CONN = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
CURSOR = CONN.cursor()

# Create tables if not exist
CURSOR.execute(
    """CREATE TABLE IF NOT EXISTS patch (
             version TEXT,
             exe_hash TEXT,
             unix_time INTEGER)"""
)

CURSOR.execute(
    """CREATE TABLE IF NOT EXISTS message_log (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             version TEXT,
             sent BOOLEAN,
             unix_time_sent INTEGER,
             unix_time_logged INTEGER)"""
)

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "normal",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/infos.log",
            "mode": "a",
            "formatter": "normal",
            "maxBytes": 50 * 1024 * 1024,  # 50 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "bot": {"handlers": ["file"], "level": "INFO", "propagate": True},
        "discord": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "__main__": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "command-use": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

dictConfig(LOGGING_CONFIG)
