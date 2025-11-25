import os, time, asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from config import OWNER_ID, LOGGER
from plugins.start import media_obj_store  # correct relative import
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd  # assuming your ffmpeg wrapper is here

log = LOGGER("convert_video_format.py")


# ----------- change video format callback ----------- #
@Bot.on_callback_query(filters.regex("^change_video_format$") & filters.user(OWNER_ID))
async def change_video_format_using_ffmpeg(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    # check media
    if user_id not in media_obj_store:
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    video_message = media_obj_store[user_id]
    start_time = time.time()

    # cleanup old messages before starting
    await cleanup_system(client, user_id)

    # download media if not already downloaded
    if not hasattr(video_message, "downloaded_file"):
        video_message.downloaded_file = await video_message.download(
            progress=progress_bar,
            progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ...")
        )

    # ask user which format to export
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴍᴋᴠ •", callback_data="format_mkv"),
            InlineKeyboardButton("• ᴍᴘ4 •", callback_data="format_mp4")
        ]
    ])
    await query.message.edit_text("🧩 sᴇʟᴇᴄᴛ ᴇxᴘᴏʀᴛ ғᴏʀᴍᴀᴛ:", reply_markup=markup)


# ----------- actual format conversion ----------- #
@Bot.on_callback_query(filters.regex("^format_(mkv|mp4)$") & filters.user(OWNER_ID))
async def convert_video_format(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    if user_id not in media_obj_store:
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    video_message = media_obj_store[user_id]
    input_path = getattr(video_message, "downloaded_file", None)

    # safety check
    if not input_path or not os.path.exists(input_path):
        start_time = time.time()
        input_path = await video_message.download(
            progress=progress_bar,
            progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ...")
        )
        video_message.downloaded_file = input_path

    input_ext = os.path.splitext(input_path)[1].lower().replace(".", "")
    target_ext = query.data.split("_")[1]  # "mp4" or "mkv"

    # skip if already in desired format
    if input_ext == target_ext:
        return await query.message.answer("ℹ️ ᴠɪᴅᴇᴏ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜɪs ғᴏʀᴍᴀᴛ!", show_alert=True)

    # cleanup old converted messages before processing
    await cleanup_system(client, user_id)

    # build new filename
    new_filename = f"{client.filename}.{target_ext}".replace("{episode}", str(client.episode))
    output_path = os.path.join(os.path.dirname(input_path), new_filename)

    # notify user
    status_msg = await query.message.edit_text(f"🔄 ᴄᴏɴᴠᴇʀᴛɪɴɢ ᴠɪᴅᴇᴏ ᴛᴏ {target_ext.upper()}...")

    # run ffmpeg
    success, rc, out, err = await run_cmd([
        "ffmpeg", "-i", input_path, "-c", "copy", output_path
    ])

    if not success:
        await status_msg.edit_text(f"ᴄᴏɴᴠᴇʀᴛɪᴏɴ ғᴀɪʟᴇᴅ ʀᴇᴀsᴏɴ:\n{err}")
        return

    # final output
    try:
        await client.send_document(
            user_id,
            output_path,
            thumb=client.thumb,
            caption=None,
            progress=progress_bar,
            progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ...")
        )
        await status_msg.edit_text(f"✅ ᴠɪᴅᴇᴏ ᴄᴏɴᴠᴇʀᴛᴇᴅ!")

    except Exception as e:
        log.exception("Failed to send formatted video")
        await status_msg.edit_text(f"❌ Sᴇɴᴅ ғᴀɪʟᴇᴅ: {e}")

    finally:
        # remove output file and token; keep original file removal optional
        await cleanup_system(client, query.from_user.id, [output_path])
        
    