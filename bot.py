from aiohttp import web
from plugins import web_server
from pyrogram import Client
from pyrogram.enums import ParseMode
from datetime import datetime
from database import MongoDB
import pyrogram.utils
import sys
from config import (
    API_HASH, API_ID, LOGGER, TELEGRAM_TOKEN, TG_BOT_WORKERS,
    PORT, FILENAME as DEFAULT_FILENAME, THUMB as DEFAULT_THUMB,
    DB_URL, DB_NAME
)

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=API_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TELEGRAM_TOKEN
        )
        self.LOGGER = LOGGER
        self.mongodb = MongoDB(DB_URL, DB_NAME)
        # default values first
        self.thumb = DEFAULT_THUMB
        self.filename = DEFAULT_FILENAME 
        self.episode = 174
        self.username = None
        self.uptime = None

    async def start(self):
        await super().start()
        self.uptime = datetime.now()

        # Load settings from MongoDB safely
        try:
            await self.load_settings()
            self.LOGGER(__name__).info("✅ Settings loaded from MongoDB.")
        except Exception as e:
            self.LOGGER(__name__).warning(
                f"⚠️ Failed to load settings from MongoDB. Using default config values. Error: {e}"
            )
            self.thumb = DEFAULT_THUMB
            self.filename = DEFAULT_FILENAME

        # Get bot info
        try:
            me = await self.get_me()
            self.username = me.username
            self.LOGGER(__name__).info(f"Bot running as @{self.username}")
        except Exception as e:
            self.LOGGER(__name__).error(f"Failed to get bot info: {e}")

        self.set_parse_mode(ParseMode.HTML)

        # Log bot banner
        self.LOGGER(__name__).info()

        # Start web server
        try:
            app_runner = web.AppRunner(await web_server())
            await app_runner.setup()
            site = web.TCPSite(app_runner, "0.0.0.0", PORT)
            await site.start()
            self.LOGGER(__name__).info(f"Web server started on 0.0.0.0:{PORT}")
        except Exception as e:
            self.LOGGER(__name__).error(f"Failed to start web server: {e}")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    async def load_settings(self):
        """Load thumb and filename from MongoDB; fallback handled in start()"""
        data = await self.mongodb.get_settings()
        self.thumb = data.get("thumb", self.thumb)
        self.filename = data.get("filename", self.filename)
        self.episode = data.get("episode", self.episode)

    async def update_setting(self, key, value):
        """Update MongoDB and in-memory attribute"""
        try:
            await self.mongodb.update_setting(key, value)
            setattr(self, key, value)
            self.LOGGER(__name__).info(f"Updated setting {key} = {value}")
        except Exception as e:
            self.LOGGER(__name__).warning(f"Failed to update setting {key}: {e}")