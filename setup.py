import os
import pathlib
import sqlite3
import datetime
import pytz
import shutil

# Ensure the logs directory exists before configuring logging
BASE_DIR = pathlib.Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OLD_DATABASE_DIR = DATA_DIR / "old_database"
OLD_DATABASE_DIR.mkdir(exist_ok=True)

# Path settings
BASE_DIRECTORY = "data"
BASE_PATH = pathlib.Path(BASE_DIRECTORY).absolute()
STORAGE_DIRECTORY = BASE_PATH / "stored"
DOWNLOAD_DIRECTORY = BASE_PATH / "download"
STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Database paths
DATABASE_PATH = BASE_PATH / "patchdatabase.db"
OLD_DATABASE_PATH = OLD_DATABASE_DIR / "patchdatabase.db.old"
NEW_DATABASE_PATH = BASE_PATH / "patchdatabase_v2.db"

# Check if migration is needed
migration_needed = DATABASE_PATH.exists()

# Move the existing database to the old_database directory if it exists
if migration_needed:
    shutil.move(DATABASE_PATH, OLD_DATABASE_PATH)

# SQLite connections
if migration_needed:
    CONN_V1 = sqlite3.connect(OLD_DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    CURSOR_V1 = CONN_V1.cursor()

CONN_V2 = sqlite3.connect(NEW_DATABASE_PATH)
CURSOR_V2 = CONN_V2.cursor()

# Create new tables in the new database
CURSOR_V2.execute(
    """CREATE TABLE IF NOT EXISTS patch (
             version TEXT,
             exe_hash TEXT,
             unix_time INTEGER)"""
)

CURSOR_V2.execute(
    """CREATE TABLE IF NOT EXISTS message_log (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             version TEXT,
             sent BOOLEAN,
             unix_time_sent INTEGER,
             unix_time_logged INTEGER)"""
)

# Function to convert date-time strings to Unix timestamps
def convert_to_unix(date_time_str):
    dt_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]
    utc_plus_12 = pytz.timezone("Etc/GMT-12")

    for dt_format in dt_formats:
        try:
            dt = datetime.datetime.strptime(date_time_str, dt_format)
            dt = utc_plus_12.localize(dt)
            unix_timestamp = int(dt.timestamp())
            return unix_timestamp
        except ValueError:
            continue

    raise ValueError(
        f"Time data '{date_time_str}' does not match any of the formats: {dt_formats}"
    )


# Migrate data from the old database to the new one
def migrate_data():
    # Migrate patch table
    CURSOR_V1.execute("SELECT version, exe_hash, date_time FROM patch")
    patches = CURSOR_V1.fetchall()
    for version, exe_hash, date_time in patches:
        unix_time = convert_to_unix(date_time)
        CURSOR_V2.execute(
            "INSERT INTO patch (version, exe_hash, unix_time) VALUES (?, ?, ?)",
            (version, exe_hash, unix_time),
        )

    # Migrate message_log table
    CURSOR_V1.execute(
        "SELECT id, version, sent, timestamp_sent, timestamp_logged FROM message_log"
    )
    messages = CURSOR_V1.fetchall()
    for message_id, version, sent, timestamp_sent, timestamp_logged in messages:
        unix_time_sent = convert_to_unix(timestamp_sent) if timestamp_sent else None
        unix_time_logged = (
            convert_to_unix(timestamp_logged) if timestamp_logged else None
        )
        CURSOR_V2.execute(
            "INSERT INTO message_log (id, version, sent, unix_time_sent, unix_time_logged) VALUES (?, ?, ?, ?, ?)",
            (message_id, version, sent, unix_time_sent, unix_time_logged),
        )

    # Commit the changes
    CONN_V2.commit()


# Perform the migration if needed
if migration_needed:
    migrate_data()
    # Close the old database connection
    CONN_V1.close()

# Close the new database connection
CONN_V2.close()

if migration_needed:
    print(
        "Database migration from old to v2 using unix timestamps completed successfully."
    )
