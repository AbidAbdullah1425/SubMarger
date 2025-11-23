from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL, DB_NAME

class MongoDB:
  def __init__(self, uri, name):
    self.db = AsyncIOMotorClient(uri)[name] 
    self.collection = self.db["settings"] 
  
  
  async def get_settings(self):
    data = await self.collection.find_one({"_id": "bot_settings"})
    return data or {}
  
  async def update_settings(self, key, value):
    await self.collection.update_one(
      {"_id": "bot_settings"},
      {"$set": {key: value}},
      upsert=True
    )