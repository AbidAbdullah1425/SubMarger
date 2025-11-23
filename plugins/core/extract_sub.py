import os, time, asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from config import OWNER_ID, LOGGER
from plugins.start import media_obj_store
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd
from plugins.get_subtitle_stream import get_subtitle_streams  # your function to get subtitle streams

log = LOGGER("SubtitleExtractor")

# ----------- extract subtitle callback ----------- #
@Bot.on_callback_query(filters.regex("^extract_sub$") & filters.user(OWNER_ID))
async def extract_subtitle_using_ffmpeg(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id
    log.info(f"[START] Subtitle extraction triggered by user {user_id}")

    if user_id not in media_obj_store:
        log.warning(f"No media found in memory for user {user_id}")
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    video_message = media_obj_store[user_id]
    start_time = time.time()

    try:
        if not hasattr(video_message, "downloaded_file"):
            log.info(f"Downloading media for user {user_id}...")
            video_message.downloaded_file = await video_message.download(
                progress=progress_bar,
                progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ...")
            )
            log.info(f"Download complete: {video_message.downloaded_file}")
        file_path = video_message.downloaded_file

        log.info(f"Getting subtitle streams for file: {file_path}")
        streams = await get_subtitle_streams(file_path)
        log.info(f"Subtitle streams found: {streams}")
        if not streams:
            log.warning(f"No subtitle streams detected in file {file_path}")
            return await query.message.edit_text("⚠️ ɴᴏ sᴜʙᴛɪᴛʟᴇ ғᴏᴜɴᴅ.")

        buttons = [
            [InlineKeyboardButton(f"{s['title']} ({s['lang']})", callback_data=f"subsel|{file_path}|{s['index']}")]
            for s in streams
        ]
        await query.message.edit_text("🎞 sᴇʟᴇᴄᴛ sᴜʙᴛɪᴛʟᴇ:", reply_markup=InlineKeyboardMarkup(buttons))
        log.info("Subtitle selection buttons sent to user")

    except Exception as e:
        log.exception(f"Error during download or subtitle stream extraction: {e}")
        await query.message.edit_text(f"❌ ᴇʀʀᴏʀ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ: {e}")


# ----------- choose format ----------- #
@Bot.on_callback_query(filters.regex("^subsel\\|") & filters.user(OWNER_ID))
async def choose_format(client: Client, query: CallbackQuery):
    await query.answer()
    _, file_path, stream_index = query.data.split("|")
    log.info(f"User {query.from_user.id} selected stream {stream_index} for file {file_path}")

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴀss •", callback_data=f"ffmpeg_export|{file_path}|{stream_index}|ass"),
            InlineKeyboardButton("• sʀᴛ •", callback_data=f"ffmpeg_export|{file_path}|{stream_index}|srt")
        ]
    ])
    await query.message.edit_text("🧩 sᴇʟᴇᴄᴛ ᴇxᴘᴏʀᴛ ғᴏʀᴍᴀᴛ:", reply_markup=markup)
    log.info(f"Export format buttons sent for stream {stream_index}")


# ----------- export subtitle ----------- #
@Bot.on_callback_query(filters.regex("^ffmpeg_export\\|") & filters.user(OWNER_ID))
async def export_subtitle(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        _, file_path, stream_index, fmt = query.data.split("|")
    except ValueError:
        log.error("Invalid callback data format")
        return await query.message.edit_text("⚠️ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ ғᴏʀᴍᴀᴛ!")

    output_path = file_path.rsplit(".", 1)[0] + f".{fmt}"
    log.info(f"Exporting subtitle: file={file_path}, stream={stream_index}, format={fmt}, output={output_path}")
    status_msg = await query.message.edit_text(f"⚙️ ᴇxᴛʀᴀᴄᴛɪɴɢ {fmt.upper()}...", parse_mode=ParseMode.HTML)

    cmd = ["ffmpeg", "-y", "-i", file_path, "-map", f"0:s:{stream_index}", output_path]
    log.info(f"Running ffmpeg command: {' '.join(cmd)}")
    rc, out, err = await run_cmd(cmd)
    log.info(f"FFmpeg returned code {rc}")

    if rc != 0 or not os.path.exists(output_path):
        log.error(f"FFmpeg failed for {file_path} -> {output_path}, err={err}")
        await status_msg.edit_text(f"❌ ғᴀɪʟᴇᴅ!\n<code>{err[:800]}</code>", parse_mode=ParseMode.HTML)
        await cleanup_system(client, query.from_user.id, [output_path, file_path])
        return

    try:
        if getattr(client, "thumb", None):
            log.info(f"Sending subtitle file to user {query.from_user.id}")
            await client.send_document(
                query.from_user.id,
                output_path,
                thumb=client.thumb,
                caption=f"Sᴜʙᴛɪᴛʟᴇ Exᴘᴏʀᴛᴇᴅ ({fmt.upper()})",
                progress=progress_bar,
                progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇ...")
            )
            log.info(f"Subtitle sent successfully: {output_path}")
        else:
            log.warning("Thumbnail not set for sending document")
            await status_msg.edit_text("⚠️ ᴛʜᴜᴍʙɴᴀɪʟ ɪsɴ'ᴛ sᴇᴛ")

        await status_msg.edit_text(f"✅ ᴇxᴛʀᴀᴄᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟʟ!")

    except Exception as e:
        log.exception(f"Failed to send subtitle file: {e}")
        await status_msg.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ: {e}")

    finally:
        log.info(f"Cleaning up temporary files: {[output_path, file_path]}")
        await cleanup_system(client, query.from_user.id, [output_path, file_path])
        log.info("[END] Subtitle extraction flow complete")