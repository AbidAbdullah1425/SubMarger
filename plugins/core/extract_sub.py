import os
import time
import asyncio
import uuid
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from config import OWNER_ID, LOGGER
from plugins.start import media_obj_store
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd
from plugins.get_subtitle_stream import get_subtitle_streams

log = LOGGER("extract_sub.py")

# token -> filepath map (keeps callback_data tiny)
file_token_map: dict[str, str] = {}


def make_token() -> str:
    # short unique token (8 hex chars)
    return uuid.uuid4().hex[:8]


# ---------- STEP 1: extract subtitle streams ----------
@Bot.on_callback_query(filters.regex("^extract_sub$") & filters.user(OWNER_ID))
async def extract_subtitle_using_ffmpeg(client: Client, query: CallbackQuery):
    await query.answer()
    uid = query.from_user.id
    log.info(f"[START] Subtitle extraction requested by {uid}")

    if uid not in media_obj_store:
        log.warning(f"No media in memory for {uid}")
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    msg = media_obj_store[uid]
    start = time.time()

    try:
        # download once
        if not hasattr(msg, "downloaded_file"):
            log.info(f"Downloading media for user {uid}...")
            msg.downloaded_file = await msg.download(
                progress=progress_bar,
                progress_args=(start, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...")
            )
            log.info(f"Downloaded: {msg.downloaded_file}")

        file_path = msg.downloaded_file
        streams = await get_subtitle_streams(file_path)
        log.info(f"Streams found: {streams}")

        if not streams:
            log.warning(f"No subtitle streams found in {file_path}")
            return await query.message.edit_text("⚠️ Nᴏ sᴜʙᴛɪᴛʟᴇ ғᴏᴜɴᴅ.")

        # create token and store mapping
        token = make_token()
        file_token_map[token] = file_path
        log.info(f"Token {token} → {file_path}")

        # build tiny callback data: subsel|<token>|<index>
        buttons = [
            [
                InlineKeyboardButton(
                    f"{s['title']} ({s['lang']})",
                    callback_data=f"subsel|{token}|{s['index']}"
                )
            ] for s in streams
        ]

        await query.message.edit_text(
            "🎞 Sᴇʟᴇᴄᴛ sᴜʙᴛɪᴛʟᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        log.info("Buttons sent")

    except Exception as e:
        log.exception("Error during subtitle extraction")
        await query.message.edit_text(f"❌ ᴇʀʀᴏʀ: {e}")


# ---------- STEP 2: choose format ----------
@Bot.on_callback_query(filters.regex("^subsel\\|") & filters.user(OWNER_ID))
async def choose_format(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        _, token, stream_index = query.data.split("|")
    except ValueError:
        return await query.message.edit_text("⚠️ Invalid callback data!")

    file_path = file_token_map.get(token)
    if not file_path or not os.path.exists(file_path):
        log.warning(f"Missing file for token {token}")
        # cleanup possible stale token
        file_token_map.pop(token, None)
        return await query.message.edit_text("⚠️ Fɪʟᴇ ɴᴏᴛ ᴏɴ sᴇʀᴠᴇʀ ᴀɴʏᴍᴏʀᴇ.")

    log.info(f"User {query.from_user.id} selected stream {stream_index} for {file_path}")

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ASS •", callback_data=f"ffmpeg_export|{token}|{stream_index}|ass"),
            InlineKeyboardButton("• SRT •", callback_data=f"ffmpeg_export|{token}|{stream_index}|srt")
        ]
    ])

    await query.message.edit_text("🧩 Sᴇʟᴇᴄᴛ ғᴏʀᴍᴀᴛ:", reply_markup=markup)


# ---------- STEP 3: export subtitle ----------
@Bot.on_callback_query(filters.regex("^ffmpeg_export\\|") & filters.user(OWNER_ID))
async def export_subtitle(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        _, token, stream_index, fmt = query.data.split("|")
    except ValueError:
        log.error("Invalid export callback format")
        return await query.message.edit_text("⚠️ Invalid callback data!")

    file_path = file_token_map.get(token)
    if not file_path or not os.path.exists(file_path):
        log.warning(f"Token missing or file gone: {token}")
        file_token_map.pop(token, None)
        return await query.message.edit_text("⚠️ Fɪʟᴇ ɴᴏᴛ ᴏɴ sᴇʀᴠᴇʀ ᴀɴʏᴍᴏʀᴇ.")

    output_path = file_path.rsplit(".", 1)[0] + f".{fmt}"
    log.info(f"Exporting subtitle: file={file_path}, stream={stream_index}, fmt={fmt}, out={output_path}")

    status = await query.message.edit_text(f"⚙️ Exᴛʀᴀᴄᴛɪɴɢ {fmt.upper()}...")

    cmd = ["ffmpeg", "-y", "-i", file_path, "-map", f"0:s:{stream_index}", output_path]
    success, rc, out, err = await run_cmd(cmd)
    log.info(f"ffmpeg rc={rc}")

    if not success or not os.path.exists(output_path):
        log.error(f"ffmpeg failed: {err}")
        await status.edit_text(f"❌ Fᴀɪʟᴇᴅ!\n<code>{err[:800]}</code>")
        # cleanup and remove token
        await cleanup_system(client, query.from_user.id, [output_path])
        file_token_map.pop(token, None)
        return

    try:
        await client.send_document(
            query.from_user.id,
            output_path,
            caption=f"Sᴜʙᴛɪᴛʟᴇ Exᴘᴏʀᴛᴇᴅ ({fmt.upper()})",
            progress=progress_bar,
            progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ...")
        )
        await status.edit_text("✅ Dᴏɴᴇ!")

    except Exception as e:
        log.exception("Failed to send subtitle")
        await status.edit_text(f"❌ Sᴇɴᴅ ғᴀɪʟᴇᴅ: {e}")

    finally:
        # remove output file and token; keep original file removal optional
        await cleanup_system(client, query.from_user.id, [output_path])
        file_token_map.pop(token, None)
        log.info(f"Cleaned up token {token} and output {output_path}")