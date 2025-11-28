import os, time
from pyrogram import filters, Client
from pyrogram.types import CallbackQuery, ForceReply
from bot import Bot
from config import OWNER_ID, FONT, DOWNLOAD_DIR
from plugins.start import media_obj_store
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd
from plugins.core.change_sub_format import change_sub_format

# --- pending reply & video cache ---
pending_sub_reply = {}
video_paths = {}

# ----------- add subtitle button below streams ----------- #
@Bot.on_callback_query(filters.regex("^add_sub$") & filters.user(OWNER_ID))
async def add_subtitle_request(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    if user_id not in media_obj_store:
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    # download video only once per user
    if user_id not in video_paths:
        start_time = time.time()
        video_name = client.filename.format(episode=client.episode)
        video_path = os.path.join(DOWNLOAD_DIR, video_name)
        await media_obj_store[user_id].download(
            file_name=video_path,
            progress=progress_bar,
            progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ...")
        )
        video_paths[user_id] = video_path

    pending_sub_reply[user_id] = query.message.message_id

    await query.message.edit_text(
        "📩 ʀᴇᴘʟʏ ᴡɪᴛʜ ʏᴏᴜʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ (srt or ass).",
        reply_markup=ForceReply(True)
    )


# ----------- handle force reply for adding subtitle ----------- #
@Bot.on_message(filters.user(OWNER_ID) & filters.reply)
async def handle_add_sub_reply(client: Client, message):
    user_id = message.from_user.id
    reply_msg = message.reply_to_message

    if user_id not in pending_sub_reply or reply_msg.message_id != pending_sub_reply[user_id]:
        return

    video_path = video_paths.get(user_id)
    if not video_path:
        return await message.reply("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    try:
        start_time = time.time()
        sub_path = await message.download(
            dir=DOWNLOAD_DIR,
            progress=progress_bar,
            progress_args=(start_time, message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ...")
        )

        # convert to ASS if not already
        sub_ext = os.path.splitext(sub_path)[1].lower().replace(".", "")
        if sub_ext != "ass":
            new_sub_path = await change_sub_format(sub_path, "ass", DOWNLOAD_DIR)
            if not os.path.exists(new_sub_path):
                return await message.reply("❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏɴᴠᴇʀᴛ sᴜʙᴛɪᴛʟᴇ.")
            sub_path = new_sub_path

        # final output video path
        output_path = os.path.join(DOWNLOAD_DIR, FILENAME.format(episode=client.episode))

        # ffmpeg command to attach subtitle with font
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", sub_path,
            "-attach", FONT,
            "-metadata:s:t", "mimetype=application/x-truetype-font",
            "-map", "0", "-map", "1",
            "-c", "copy",
            "-metadata:s", 'title="HeavenlySubs"',
            "-metadata:s", "language=eng",
            "-disposition:s", "default",
            output_path
        ]

        success, out, err = await run_cmd(cmd)
        if not success or not os.path.exists(output_path):
            return await message.reply(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴀᴅᴅ sᴜʙᴛɪᴛʟᴇ:\n{err}")

        await message.reply(f"✅ sᴜʙᴛɪᴛʟᴇ ᴀᴅᴅᴇᴅ!\n\n📁 {os.path.basename(output_path)}")

        # upload to PM
        await client.send_document(
            OWNER_ID,
            output_path,
            caption=None,
            thumb=cluent.thumb,
            progress=progress_bar,
            progress_args=(time.time(), message, "ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇ...")
        )

    finally:
        cleanup_system([video_path, output_path, sub_path])
        del pending_sub_reply[user_id]
        del video_paths[user_id]