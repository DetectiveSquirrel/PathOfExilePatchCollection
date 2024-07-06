import logging
import aiohttp
import asyncio
import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import discord
from discord.ext import commands
import hashlib
import settings

# Initialize the logger
logger = logging.getLogger(__name__)

name = "Path of Exile Patch Downloader"
version = "1.0"

extensions = ["cogs.admincommands", "cogs.membercommands"]


async def fetch_patch():
    try:
        reader, writer = await asyncio.open_connection("patch.pathofexile.com", 12995)
        writer.write(bytes([1, 6]))
        await writer.drain()
        data = await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        patch = data[35 : 35 + data[34] * 2].decode("utf-16le").split("/")[-2]
        logger.debug(f"Fetched patch version directly: {patch}")
        return patch
    except Exception as e:
        logger.error(f"An error occurred while fetching patch: {e}")
        return None


async def fetch_patch_from_github():
    url = "https://raw.githubusercontent.com/poe-tool-dev/latest-patch-version/main/latest.txt"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                version = await response.text()
                version = version.strip()
                logger.debug(f"Fetched patch version from GitHub: {version}")
                return version
    except Exception as e:
        logger.error(f"An error occurred while fetching patch from GitHub: {e}")
        return None


intents = discord.Intents.all()


async def patch_downloader():
    logger.info("Started Patch Downloader Task.")
    while True:
        try:
            version = (
                await fetch_patch()
                if settings.FETCH_DIRECTLY
                else await fetch_patch_from_github()
            )
            if version and version.lower() != "none":
                settings.CURSOR.execute(
                    "SELECT * FROM patch WHERE version=?", (version,)
                )
                result = settings.CURSOR.fetchone()

                if not result:
                    exe_url = f"https://patch.poecdn.com/{version}/PathOfExile.exe"
                    zip_name = f"{version}.zip"
                    logger.debug(f"Exe URL: {exe_url}")
                    logger.debug(f"Zip Name: {zip_name}")

                    if not (settings.DOWNLOAD_DIRECTORY / zip_name).exists():
                        async with aiohttp.ClientSession() as session:
                            async with session.get(exe_url) as response:
                                if response.status != 200:
                                    logger.error(
                                        f"Failed to download executable. Status code: {response.status}"
                                    )
                                    continue
                                exe_path = (
                                    settings.DOWNLOAD_DIRECTORY / "PathOfExile.exe"
                                )
                                with exe_path.open("wb") as f:
                                    f.write(await response.read())

                        if exe_path.stat().st_size < 3 * 1024 * 1024:
                            logger.info(
                                f"Raw file `{exe_path}` is smaller than 3MB. Skipping download."
                            )
                            exe_path.unlink()
                            continue

                        hash_object = hashlib.sha256()
                        with exe_path.open("rb") as f:
                            hash_object.update(f.read())
                        exe_hash = hash_object.hexdigest()
                        logger.debug(f"Exe Hash: {exe_hash}")

                        zip_path = settings.DOWNLOAD_DIRECTORY / zip_name
                        with ZipFile(
                            zip_path, "w", ZIP_DEFLATED, compresslevel=9
                        ) as zipf:
                            zipf.write(exe_path, arcname="PathOfExile.exe")

                        # Insert data into SQLite with Unix timestamps
                        current_unix_time = int(datetime.datetime.now().timestamp())
                        settings.CURSOR.execute(
                            "INSERT INTO patch (version, exe_hash, unix_time) VALUES (?, ?, ?)",
                            (version, exe_hash, current_unix_time),
                        )
                        settings.CURSOR.execute(
                            "INSERT INTO message_log (version, sent, unix_time_sent, unix_time_logged) VALUES (?, ?, ?, ?)",
                            (version, False, None, current_unix_time),
                        )
                        settings.CONN.commit()

                        # Move the ZIP file to the storage directory
                        storage_zip_path = settings.STORAGE_DIRECTORY / zip_name
                        zip_path.replace(storage_zip_path)

                        # Clean up the leftover .exe file
                        exe_path.unlink()

                        logger.info(
                            f"New version {version} downloaded, stored, and cleaned up."
                        )
                    else:
                        logger.info(f"ZIP file for version {version} already exists.")
            else:
                logger.error(f"Invalid or no version found: {version}")
        except Exception as e:
            logger.error(f"Error in patch downloader: {e}")

        logger.debug(f"Patch Downloader waiting {settings.TIME_INTERVAL_TO_DOWNLOAD}s.")
        await asyncio.sleep(settings.TIME_INTERVAL_TO_DOWNLOAD)


async def send_pending_messages(bot):
    logger.info("Started Pending Message Task.")
    while True:
        if bot.is_ready():
            logger.debug("Bot is ready. Checking for pending messages...")

            # Fetch pending messages
            settings.CURSOR.execute("SELECT * FROM message_log WHERE sent=0")
            pending_messages = settings.CURSOR.fetchall()
            logger.debug(f"Found {len(pending_messages)} pending messages.")

            for message in pending_messages:
                version = message[1]
                storage_zip_path = settings.STORAGE_DIRECTORY / f"{version}.zip"
                logger.debug(
                    f"Processing message for version {version} with id {message[0]}."
                )

                try:
                    with storage_zip_path.open("rb") as fp:
                        logger.debug(f"Uploading file for version {version}...")
                        file_upload = await bot.get_channel(settings.CHANNEL_ID).send(
                            file=discord.File(fp, filename=f"{version}.zip")
                        )
                        attachment_url = file_upload.attachments[0].url
                        logger.debug(
                            f"File uploaded for version {version}. Attachment URL: {attachment_url}"
                        )

                        # Fetch exe_hash from the database
                        settings.CURSOR.execute(
                            "SELECT exe_hash FROM patch WHERE version=?", (version,)
                        )
                        exe_hash = settings.CURSOR.fetchone()
                        exe_hash = exe_hash[0] if exe_hash else "N/A(uh oh)"

                        embed = discord.Embed(
                            color=discord.Color(0x4DEFF2),
                            title="PathOfExile.exe Version Change Detected",
                            url="https://www.pathofexile.com/forum/view-forum/patch-notes",
                        )
                        embed.add_field(
                            name="Version:", value=f"`{version}`", inline=True
                        )
                        embed.add_field(
                            name="Zip:",
                            value=f"[PathOfExile.exe]({attachment_url})",
                            inline=True,
                        )
                        embed.add_field(
                            name="When:",
                            value=f"<t:{int(datetime.datetime.now().timestamp())}:R>",
                            inline=True,
                        )
                        embed.add_field(
                            name="Exe Hash:", value=f"`{exe_hash}`", inline=False
                        )
                        embed.add_field(
                            name="*Source:*",
                            value="*[PR's for this project can be done so here, I'm not watching them.](https://github.com/DetectiveSquirrel/PathOfExilePatchCollection)*",
                            inline=False,
                        )

                        message_content = f"<@&{settings.NOTIFICATION_ROLE}> PathOfExile.exe {version}"
                        logger.debug(
                            f"Sending message to notifier channel for version {version}..."
                        )
                        await bot.get_channel(settings.CHANNEL_NOTIFIER_ID).send(
                            message_content, embed=embed
                        )
                        logger.info(
                            f"Message sent to notifier channel for version {version}."
                        )

                        # Update the message log entry to mark it as sent
                        logger.debug(
                            f"Updating database for message id {message[0]}..."
                        )
                        settings.CURSOR.execute(
                            "UPDATE message_log SET sent = ?, unix_time_sent = ? WHERE id = ?",
                            (
                                True,
                                int(datetime.datetime.now().timestamp()),
                                message[0],
                            ),
                        )
                        settings.CONN.commit()
                        logger.debug(
                            f"Database updated for message id {message[0]}: marked as sent."
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to send message for version {version}: {e}. Continuing to the next message..."
                    )

        else:
            logger.debug("Bot is not ready.")

        logger.debug(f"Pending Message waiting {settings.TIME_INTERVAL_TO_MESSAGE}s.")
        await asyncio.sleep(settings.TIME_INTERVAL_TO_MESSAGE)


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Startup message
        logger.info(f"Starting up bot '{name} v{version}'")
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.loop.create_task(patch_downloader())
        self.loop.create_task(send_pending_messages(self))

    async def on_ready(self):
        logger.info(f"{self.user.name} has connected to Discord!")

        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension '{extension}'")
            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"Extension '{extension}' is already loaded")
            except commands.ExtensionNotFound:
                logger.error(f"Extension '{extension}' not found")
            except commands.NoEntryPointError:
                logger.error(f"Extension '{extension}' does not have a setup function")
            except commands.ExtensionFailed as e:
                logger.error(f"Extension '{extension}' failed to load: {e}")

        self.tree.copy_global_to(guild=settings.BASE_SERVER_ID)
        await self.tree.sync(guild=settings.BASE_SERVER_ID)


async def main():
    async with MyBot(command_prefix="!", intents=intents) as bot:
        await bot.start(settings.DISCORD_API_SECRET, reconnect=True)


if __name__ == "__main__":
    asyncio.run(main())
