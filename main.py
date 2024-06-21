import logging
import os
import sqlite3
import urllib.request
import datetime
import requests
from zipfile import ZipFile, ZIP_DEFLATED
import time
import socket
import discord
from discord.ext import commands
import asyncio
import configparser
import hashlib
import uuid

# Set up logging to flush immediately
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler()])

# Adapter function
def adapt_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# Converter function
def convert_datetime(s):
    return datetime.datetime.strptime(s.decode(), "%Y-%m-%d %H:%M:%S")

# Register the adapter and converter
sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

config = configparser.ConfigParser()
config.read('config.ini')

# Set base directory (relative path)
base_directory = 'data'

# bot token and channel ID
token = config.get('DISCORD', 'TOKEN')
channelID = int(config.get('DISCORD', 'CHANNELID'))  # Convert to int because Discord IDs are integers
channelNotifierID = int(config.get('DISCORD', 'CHANNELNOTIFIERID'))  # Convert to int because Discord IDs are integers
roleNotificationID = int(config.get('DISCORD', 'NOTIFICATIONROLE'))  # Convert to int because Discord IDs are integers

# Specify the time interval (in seconds) for running the code
time_interval = 60  # Change this value as needed
last_task_time_threshold = 120  # time where no tasks are running before starting a new one

# Get the absolute path of the current working directory
cwd = os.getcwd()
base_path = os.path.join(cwd, base_directory)

# Create base directory if it doesn't exist
os.makedirs(base_path, exist_ok=True)

# Set storage and download directories (relative paths)
storage_directory = os.path.join(base_directory, 'stored')
download_directory = os.path.join(base_directory, 'download')

# Get the absolute paths of storage and download directories
storage_path = os.path.join(cwd, storage_directory)
download_path = os.path.join(cwd, download_directory)

# Create storage and download directories if they don't exist
os.makedirs(storage_path, exist_ok=True)
os.makedirs(download_path, exist_ok=True)

# Create connection and cursor to SQLite database
conn = sqlite3.connect(os.path.join(base_path, 'patchdatabase.db'), detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()

# Create table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS patch
             (version text, exe_hash text, date_time timestamp)''')

def generate_task_id():
    return uuid.uuid4().hex[:6].upper()

def log(message):
    logging.info(message)

def debug_log(message, debug_mode):
    if debug_mode:
        log(f"Debug[\"{message}\"]")

# startup message
log(f"Patch downloader started.")

# Configuration variables
fetch_directly = False  # Set to True for fetching directly from GGG servers, False for fetching from GitHub
log_only_new_versions = True  # Set to True to log only when a new version is downloaded
debug_mode = False  # Set to True to enable debug logging

def fetch_patch():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("patch.pathofexile.com", 12995))
            s.sendall(bytes([1, 6]))
            data = s.recv(1024)
            patch = data.decode('utf-8').split("/")[-2]
            return patch
    except Exception as e:
        print(f"An error occurred: {e}")

intents = discord.Intents.all()

async def monitor_tasks(bot):
    log("Task monitor started.")
    last_task_time = datetime.datetime.now()

    while True:
        debug_log(f"Checking active tasks: {len(bot.active_tasks)}", debug_mode)
        # If more than one task is running, cancel all tasks
        if len(bot.active_tasks) > 1:
            log(f"More than one task found: {len(bot.active_tasks)}. Cancelling all tasks.")
            for task in bot.active_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    log(f"Cancelled task #{bot.task_ids[task]}")
            bot.active_tasks = []
            bot.task_ids = {}

        # Check if no tasks are running for more than 2 minutes
        if not bot.active_tasks or all(task.done() for task in bot.active_tasks):
            current_time = datetime.datetime.now()
            if (current_time - last_task_time).total_seconds() > last_task_time_threshold:
                start_new_task(bot, "due to inactivity")
                last_task_time = current_time
            else:
                debug_log(f"No active tasks, but within the {last_task_time_threshold}s threshold.", debug_mode)
        else:
            last_task_time = datetime.datetime.now()

        # Wait before the next check
        await asyncio.sleep(10)

def start_new_task(bot, reason="None"):
    task_id = generate_task_id()
    log(f"Starting new task #{task_id} Reason[{reason}]")
    new_task = bot.loop.create_task(run_patch_downloader(bot, task_id))
    bot.active_tasks.append(new_task)
    bot.task_ids[new_task] = task_id
    log(f"New task #{task_id} started and added to active_tasks. Total active tasks: {len(bot.active_tasks)}")

# Discord bot setup
class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_tasks = []
        self.task_ids = {}

    async def setup_hook(self):
        log("Setting up the task monitor.")
        self.loop.create_task(monitor_tasks(self))

    async def on_ready(self):
        log(f'{self.user.name} has connected to Discord!')
        start_new_task(self)

async def run_patch_downloader(bot, task_id):
    log(f"Patch downloader task #{task_id} started.")
    while True:
        debug_log(f"Patch downloader task #{task_id} is running.", debug_mode)
        try:
            # Get latest version number
            if fetch_directly:
                version = fetch_patch()
            else:
                response = urllib.request.urlopen('https://raw.githubusercontent.com/poe-tool-dev/latest-patch-version/main/latest.txt')
                version = response.read().decode()

            # Check if version already exists in the database
            c.execute("SELECT * FROM patch WHERE version=?", (version,))
            result = c.fetchone()

            if result:
                if not log_only_new_versions:
                    log(f"Version {version} already exists in the database.")
            else:
                if version.lower() == "none":
                    log(f"Invalid version: {version}. Skipping download.")
                    continue  # Skip the download process

                # Construct the exe URL using the version
                exe_url = f"https://patch.poecdn.com/{version}/PathOfExile.exe"
                zip_name = f"{version}.zip"

                # Check if ZIP file already exists
                if os.path.exists(os.path.join(download_path, zip_name)):
                    log(f"ZIP file already exists.")
                else:
                    # Download the exe
                    response = requests.get(exe_url)
                    exe_path = os.path.join(download_path, "PathOfExile.exe")
                    with open(exe_path, 'wb') as f:
                        f.write(response.content)

                    # Check the downloaded file size, skip if less than 3MB as it shouldnt ever be that small
                    if os.path.getsize(exe_path) < 3 * 1024 * 1024:  # 3 MB
                        log(f"Raw file `{exe_path}` is smaller than 3MB.")
                        os.remove(exe_path)
                        continue  # Skip the rest due to invalid file.

                    # Calculate the hash of the downloaded exe
                    hash_object = hashlib.sha256()
                    with open(exe_path, 'rb') as f:
                        hash_object.update(f.read())
                    exe_hash = hash_object.hexdigest()

                    # Compress the downloaded exe into a ZIP file
                    zip_path = os.path.join(download_path, zip_name)
                    with ZipFile(zip_path, 'w', ZIP_DEFLATED, compresslevel=9) as zipf:
                        zipf.write(exe_path, arcname="PathOfExile.exe")

                    # Insert data into SQLite
                    c.execute("INSERT INTO patch VALUES (?, ?, ?)",
                              (version, exe_hash, datetime.datetime.now()))

                    # Save (commit) the changes
                    conn.commit()

                    # Move the ZIP file to the storage directory
                    storage_zip_path = os.path.join(storage_path, zip_name)
                    os.replace(zip_path, storage_zip_path)

                    log(f"New version {version} downloaded and stored.")

                    # Upload the ZIP file
                    with open(storage_zip_path, 'rb') as fp:

                        # Upload the file to a dump channel and copy its url
                        file_upload = await bot.get_channel(channelID).send(file=discord.File(fp, filename=zip_name))
                        attachment_url = file_upload.attachments[0].url

                        # Prepare the Discord embed message
                        embed = discord.Embed(
                            color=discord.Color(0x4deff2),
                            title="PathOfExile.exe Version Change Detected",
                            url="https://www.pathofexile.com/forum/view-forum/patch-notes",
                        )
                        embed.add_field(name="Version:", value=f"`{version}`", inline=True)
                        embed.add_field(name="Zip:", value=f"[PathOfExile.exe]({attachment_url})", inline=True)
                        embed.add_field(name="When:", value=f"<t:{int(datetime.datetime.now().timestamp())}:R>", inline=True)
                        embed.add_field(name="Exe Hash:", value=f"`{exe_hash}`", inline=False)
                        embed.add_field(name="*Source:*", value="*[PR's for this project can be done so here, I'm not watching them.](https://github.com/DetectiveSquirrel/PathOfExilePatchCollection)*", inline=False)

                        # Now we Notify
                        message = f"<@&{roleNotificationID}> PathOfExile.exe {version}"
                        await bot.get_channel(channelNotifierID).send(message, embed=embed)

            # Clear the download folder
            for file_name in os.listdir(download_path):
                file_path = os.path.join(download_path, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        except urllib.error.URLError as e:
            log(f"Error in task #{task_id}: Failed to connect to the URL.")

        except requests.exceptions.RequestException as e:
            log(f"Error in task #{task_id}: Failed to download the file.")

        except Exception as e:
            log(f"Error in task #{task_id}: {str(e)}")

        # Calculate the next scheduled check time
        next_check_time = datetime.datetime.now() + datetime.timedelta(seconds=time_interval)

        # Print the next scheduled check time
        if not log_only_new_versions:
            log(f"Next check scheduled at: {next_check_time.strftime('%Y-%m-%d %I:%M:%S %p')}")

        # Wait for the specified time interval before the next iteration
        debug_log(f"Task #{task_id} waiting {time_interval}s.", debug_mode)
        await asyncio.sleep(time_interval)

async def main():
    async with MyBot(command_prefix='!', intents=intents) as bot:
        await bot.start(token)

asyncio.run(main())
