from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import OWNER_ID

from plugins.core.auto_process import receive_sub
from plugins.start import subtitle_receiver

from plugins.start import WAITING_SUB   # wherever you stored WAITING_SUB dict




@Bot.on_message(
    filters.user(OWNER_ID) &
    (
        filters.video |
        (filters.document & filters.create(lambda _, __, m:
            m.document and m.document.file_name.lower().endswith((".srt", ".ass"))
        ))
    )
)
async def handle_reply(client, message):
    uid = message.from_user.id
    
    # user is replying with subtitle file
    if WAITING_SUB.get(uid) is True:
        return await receive_sub(client, message)

    # normal subtitle menu flow (WAITING_SUB == False)
    return await subtitle_receiver(client, message)