from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL, DB_NAME

class MongoDB:
  def __init__(self, uri, name):
    self.client = AsyncIOMotorClient(uri)
    self.db = self.client[name]
    self.collection = self.db["settings"]

  async def init_collection(self):
    """Ensure the settings doc exists (safe upsert)."""
    await self.collection.update_one(
      {"_id": "bot_settings"},
      {"$setOnInsert": {"_id": "bot_settings"}},
      upsert=True
    )

  async def get_settings(self):
    data = await self.collection.find_one({"_id": "bot_settings"})
    return data or {}

  # <-- RENAMED: singular to match Bot.update_setting calls
  async def update_setting(self, key, value):
    await self.collection.update_one(
      {"_id": "bot_settings"},
      {"$set": {key: value}},
      upsert=True
    )