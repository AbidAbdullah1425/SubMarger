from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, ForceReply
from pyrogram.enums import ParseMode

# --- STATE MANAGEMENT ---
_PENDING_REPLIES = {}  # chat_id -> {"msg_id": int, "callback": coroutine, "types": set, "exts": set}


async def force_reply(
    client: Client,
    chat_id: int,
    text: str,
    callback,                # async function to handle reply
    original_msg=None,
    allowed_types=("text",), # "text", "photo", "document", "video", etc.
    allowed_exts=()          # for documents or videos: ".mp4", ".srt", etc.
):
    """
    Send a ForceReply prompt and store callback for reply.

    allowed_types: tuple of allowed message types
    allowed_exts: tuple of allowed file extensions (for doc/video)
    """
    if original_msg:
        if isinstance(original_msg, CallbackQuery):
            await original_msg.message.delete()
            prompt_msg = await client.send_message(chat_id, text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)
        else:
            prompt_msg = await original_msg.reply_text(text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)
    else:
        prompt_msg = await client.send_message(chat_id, text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)

    _PENDING_REPLIES[chat_id] = {
        "msg_id": prompt_msg.id,
        "callback": callback,
        "types": set(allowed_types),
        "exts": set(ext.lower() for ext in allowed_exts)
    }
    return prompt_msg


@Client.on_message(filters.reply)
async def _force_reply_handler(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in _PENDING_REPLIES:
        return

    info = _PENDING_REPLIES[chat_id]

    # Only process reply to the stored prompt
    if not message.reply_to_message or message.reply_to_message.id != info["msg_id"]:
        return

    # Check type
    valid_type = False
    msg_type = None

    if "text" in info["types"] and message.text:
        valid_type = True
        msg_type = "text"
    elif "photo" in info["types"] and message.photo:
        valid_type = True
        msg_type = "photo"
    elif "document" in info["types"] and message.document:
        ext = f".{message.document.file_name.split('.')[-1].lower()}"
        if not info["exts"] or ext in info["exts"]:
            valid_type = True
            msg_type = "document"
    elif "video" in info["types"] and message.video:
        ext = f".{message.video.file_name.split('.')[-1].lower()}" if message.video.file_name else ""
        if not info["exts"] or ext in info["exts"]:
            valid_type = True
            msg_type = "video"

    if not valid_type:
        await message.reply(f"❌ Invalid reply type. Allowed types: {', '.join(info['types'])}")
        return

    try:
        await info["callback"](client, message, msg_type)
    finally:
        del _PENDING_REPLIES[chat_id]