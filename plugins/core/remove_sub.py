import os, time, asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from bot import Bot
from config import OWNER_ID
from plugins.start import media_obj_store
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd
from plugins.get_subtitle_stream import get_subtitle_streams


@Bot.on_callback_query(filters.regex("^remove_sub$") & filters.user(OWNER_ID))
async def remove_subtitles(client: Client, query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    if user_id not in media_obj_store:
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")

    video_message = media_obj_store[user_id]
    start_time = time.time()

    try:
        file_path = await video_message.download(
            progress=progress_bar,
            progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴍᴇᴅɪᴀ...")
        )

        streams = await get_subtitle_streams(file_path)
        if not streams:
            return await query.message.edit_text("⚠️ ɴᴏ sᴜʙᴛɪᴛʟᴇ ғᴏᴜɴᴅ.")

        buttons = [
            [InlineKeyboardButton(f"{s['title']} ({s['lang']})", callback_data=f"remove_one|{file_path}|{s['index']}")]
            for s in streams
        ]
        buttons.append([InlineKeyboardButton("• ʀᴇᴍᴏᴠᴇ ᴀʟʟ sᴜʙs •", callback_data=f"remove_all|{file_path}")])

        await query.message.edit_text("🎞 sᴇʟᴇᴄᴛ sᴜʙᴛɪᴛʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"❌ ᴇʀʀᴏʀ: {e}")


@Bot.on_callback_query(filters.regex("^remove_one\\|"))
async def remove_one_sub(client: Client, query: CallbackQuery):
    await query.answer()
    _, file_path, index = query.data.split("|")
    await remove_sub_common(client, query, file_path, index, remove_all=False)


@Bot.on_callback_query(filters.regex("^remove_all\\|"))
async def remove_all_subs(client: Client, query: CallbackQuery):
    await query.answer()
    _, file_path = query.data.split("|")
    await remove_sub_common(client, query, file_path, None, remove_all=True)


async def remove_sub_common(client, query, file_path, index=None, remove_all=False):
    await query.message.edit_text("⚙️ ʀᴇᴍᴏᴠɪɴɢ sᴜʙᴛɪᴛʟᴇs...")

    output_path = file_path.rsplit(".", 1)[0] + "_nosubs.mkv"
    cmd = ["ffmpeg", "-y", "-i", file_path, "-map", "0"]

    if remove_all:
        cmd += ["-map", "-0:s"]  # remove all subs
    else:
        cmd += ["-map", f"-0:s:{index}"]  # remove one

    cmd += ["-c", "copy", output_path]
    rc, out, err = await run_cmd(cmd)

    if rc != 0 or not os.path.exists(output_path):
        await query.message.edit_text(f"❌ ғᴀɪʟᴇᴅ!\n<code>{err[:800]}</code>", parse_mode=ParseMode.HTML)
        return cleanup_system([output_path, file_path])

    try:
        await client.send_document(
            query.from_user.id,
            output_path,
            thumb=getattr(client, "thumb", None),
            caption="✅ Aʟʟ Sᴜʙᴛɪᴛʟᴇs Rᴇᴍᴏᴠᴇᴅ" if remove_all else "✅ Sᴜʙᴛɪᴛʟᴇ Rᴇᴍᴏᴠᴇᴅ",
            progress=progress_bar,
            progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇ...")
        )
        await query.message.edit_text("✅ Dᴏɴᴇ!")
    except Exception as e:
        await query.message.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ: {e}")
    finally:
        cleanup_system([output_path, file_path])