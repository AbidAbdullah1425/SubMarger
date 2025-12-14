from pyrogram.types import InputFile
from pyrogram import filters
from config import LOG_FILE_NAME, OWNER_ID
from bot import Bot

@Bot.on_message(filters.command("logs") & filters.user(OWNER_ID))
async def send_logs(client, message):
    if os.path.exists(LOG_FILE_NAME):
        await client.send_document(
            message.chat.id,
            document=InputFile(LOG_FILE_NAME),
            caption=None
        )
    else:
        await message.reply_text("ʟᴏɢs ɴᴏᴛ ғᴏᴜɴᴅ!")