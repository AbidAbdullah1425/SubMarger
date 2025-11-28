from pyrogram import filters, Client
from pyrogram.types import CallbackQuery  
from bot import Bot  
from config import OWNER_ID, DOWNLOAD_DIR  
from plugins.start import media_obj_store  
from plugins.progressbar import progress_bar  
from plugins.cleanup import cleanup_system
from plugins.ffmpeg import run_cmd  
import os, time
import subprocess

# Reusable conversion function (moved inside this file to avoid circular import)
async def change_sub_format(input_path: str, target_format: str, output_dir: str) -> str:
    """
    Convert subtitle file from .srt <-> .ass
    Returns output_path
    """
    filename = os.path.basename(input_path)
    base_name, _ = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{base_name}.{target_format}")

    # Use run_cmd
    cmd = ["ffmpeg", "-y", "-i", input_path, output_path]
    success, rc, out, err = await run_cmd(cmd)
    if not success or not os.path.exists(output_path):
        raise Exception(err or "ffmpeg failed without error message")

    return output_path


@Bot.on_callback_query(filters.regex("^convert_sub_(srt|ass)$") & filters.user(OWNER_ID))  
async def convert_sub_callback(client: Client, query: CallbackQuery):  
    await query.answer()  
    user_id = query.from_user.id  

    if user_id not in media_obj_store:  
        return await query.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴍᴇᴍᴏʀʏ.")  

    video_msg = media_obj_store[user_id]  

    # Download the subtitle to DOWNLOAD_DIR  
    start_time = time.time()  
    try:  
        sub_path = await video_msg.download(  
            file_name=os.path.join(DOWNLOAD_DIR, None),  
            progress=progress_bar,  
            progress_args=(start_time, query.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ...")  
        )  
    except Exception as e:  
        return await query.message.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ:\n{e}")  

    target_format = query.data.split("_")[2]  # "srt" or "ass"  

    # Convert subtitle  
    try:  
        output_path = await change_sub_format(sub_path, target_format, DOWNLOAD_DIR)  
    except Exception as e:  
        cleanup_system([sub_path])  
        return await query.message.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏɴᴠᴇʀᴛ:\n{e}")  

    # Send converted file to owner  
    try:  
        await client.send_document(  
            OWNER_ID,  
            output_path,  
            caption=None,  
            thumb=client.thumb,
            progress=progress_bar,  
            progress_args=(time.time(), query.message, "ᴜᴘʟᴏᴀᴅɪɴɢ ғɪʟᴇ...")  
        )  
    except Exception as e:  
        await query.message.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ғɪʟᴇ:\n{e}")  

    # Cleanup downloaded and converted files  
    cleanup_system([sub_path, output_path])