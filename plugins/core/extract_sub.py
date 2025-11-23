import os, time, asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot
from config import OWNER_ID
from plugins.start import media_obj_store
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd
from plugins.get_subtitle_stream import get_subtitle_streams  # your function to get subtitle streams

# ----------- extract subtitle callback ----------- #
@Bot.on_callback_query(filters.regex("^extract_sub$") & filters.user(OWNER_ID))
async def extract_subtitle_using_ffmpeg(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    if user_id not in media_obj_store:
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    video_message = media_obj_store[user_id]
    start_time = time.time()

    # cleanup old messages
    await cleanup_system(client, user_id)

    try:
        # reuse downloaded file if exists
        if not hasattr(video_message, "downloaded_file"):
            video_message.downloaded_file = await video_message.download(
                progress=progress_bar,
                progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ...")
            )
        file_path = video_message.downloaded_file

        streams = await get_subtitle_streams(file_path)
        if not streams:
            return await query.message.edit_text("⚠️ ɴᴏ sᴜʙᴛɪᴛʟᴇ ғᴏᴜɴᴅ.")

        buttons = [
            [InlineKeyboardButton(f"{s['title']} ({s['lang']})", callback_data=f"subsel|{file_path}|{s['index']}")]
            for s in streams
        ]

        await query.message.edit_text("🎞 sᴇʟᴇᴄᴛ sᴜʙᴛɪᴛʟᴇ:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await query.message.edit_text(f"❌ ᴇʀʀᴏʀ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ: {e}")


# ----------- choose format ----------- #
@Bot.on_callback_query(filters.regex("^subsel\\|") & filters.user(OWNER_ID))
async def choose_format(client: Client, query: CallbackQuery):
    await query.answer()
    _, file_path, stream_index = query.data.split("|")

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴀss •", callback_data=f"ffmpeg_export|{file_path}|{stream_index}|ass"),
            InlineKeyboardButton("• sʀᴛ •", callback_data=f"ffmpeg_export|{file_path}|{stream_index}|srt")
        ]
    ])
    await query.message.edit_text("🧩 sᴇʟᴇᴄᴛ ᴇxᴘᴏʀᴛ ғᴏʀᴍᴀᴛ:", reply_markup=markup)


# ----------- export subtitle ----------- #
@Bot.on_callback_query(filters.regex("^ffmpeg_export\\|") & filters.user(OWNER_ID))
async def export_subtitle(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        _, file_path, stream_index, fmt = query.data.split("|")
    except ValueError:
        return await query.message.edit_text("⚠️ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ ғᴏʀᴍᴀᴛ!")

    output_path = file_path.rsplit(".", 1)[0] + f".{fmt}"
    status_msg = await query.message.edit_text(f"⚙️ ᴇxᴛʀᴀᴄᴛɪɴɢ {fmt.upper()}...", parse_mode=ParseMode.HTML)

    cmd = ["ffmpeg", "-y", "-i", file_path, "-map", f"0:s:{stream_index}", output_path]
    rc, out, err = await run_cmd(cmd)

    if rc != 0 or not os.path.exists(output_path):
        await status_msg.edit_text(f"❌ ғᴀɪʟᴇᴅ!\n<code>{err[:800]}</code>", parse_mode=ParseMode.HTML)
        await cleanup_system(client, user_id, [output_path, file_path])
        return

    try:
        # send file to user
        if getattr(client, "thumb", None):
            await client.send_document(
                query.from_user.id,
                output_path,
                thumb=client.thumb,
                caption=f"Sᴜʙᴛɪᴛʟᴇ Exᴘᴏʀᴛᴇᴅ ({fmt.upper()})",
                progress=progress_bar,
                progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇ...")
            )
        else:
            await status_msg.edit_text("⚠️ ᴛʜᴜᴍʙɴᴀɪʟ ɪsɴ'ᴛ sᴇᴛ")

        await status_msg.edit_text(f"✅ ᴇxᴛʀᴀᴄᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟʟ!")

    except Exception as e:
        await status_msg.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ: {e}")

    finally:
        await cleanup_system(client, user_id, [output_path, file_path])