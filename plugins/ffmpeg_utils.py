import os
import subprocess
import logging
from datetime import datetime
from .video_handler import user_data, logger
from .cleanup import cleanup
from config import DB_CHANNEL, MAIN_CHANNEL
from .link_generation import generate_link
from .channel_post import post_to_main_channel
from .utils import humanbytes
from .subtitle_utils import extract_subtitles
from pyrogram.errors import MessageIdInvalid, FloodWait
import asyncio

async def safe_edit_message(message, text):
    """Safely edit a message with error handling"""
    try:
        if message:
            try:
                await message.edit(text)
            except MessageIdInvalid:
                # Create new message if old one is invalid
                return await message.reply(text)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                return await safe_edit_message(message, text)
        return message
    except Exception as e:
        logger.error(f"Error updating message: {str(e)}")
        return message

async def merge_subtitles_task(client, message, user_id):
    data = user_data[user_id]
    video = data["video"]
    subtitle = data["subtitle"]
    new_name = data["new_name"]
    caption = data["caption"]
    channel_msg = data.get("channel_msg")
    output_file = f"{new_name}.mkv"

    font = 'Assist/Font/OathBold.otf'
    thumbnail = 'Assist/Images/thumbnail.jpg'

    status_msg = None
    try:
        # Initialize status messages
        status_msg = await message.reply("🔄 Processing video...")

        # Update channel msg for processing
        if channel_msg:
            channel_msg = await safe_edit_message(channel_msg, "Status: Removing existing subtitles...")

        logger.info(f"Removing existing subtitles from video for user {user_id}")
        remove_subs_cmd = [
            "ffmpeg", "-i", video,
            "-map", "0:v", "-map", "0:a?",
            "-c", "copy", "-y", "removed_subtitles.mkv"
        ]
        subprocess.run(remove_subs_cmd, check=True)

        # Update status for merging
        status_msg = await safe_edit_message(status_msg, "🔄 Merging subtitles...")
        if channel_msg:
            channel_msg = await safe_edit_message(channel_msg, "Status: Merging subtitles and fonts...")

        logger.info(f"Merging subtitles: {output_file}")
        ffmpeg_cmd = [
            "ffmpeg", "-i", "removed_subtitles.mkv",
            "-i", subtitle,
            "-attach", font, "-metadata:s:t:0", "mimetype=application/x-font-otf",
            "-map", "0", "-map", "1",
            "-metadata:s:s:0", "title=HeavenlySubs",
            "-metadata:s:s:0", "language=eng", "-disposition:s:s:0", "default",
            "-c", "copy", output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)

        # Update status for upload
        status_msg = await safe_edit_message(status_msg, "📤 Starting upload...")
        if channel_msg:
            channel_msg = await safe_edit_message(channel_msg, "Status: Starting upload...")

        start_time = datetime.now()
        last_update_time = datetime.now()
        update_interval = 7  # 7 seconds between updates

        # Upload progress callback
        async def progress_callback(current, total):
            try:
                nonlocal last_update_time, channel_msg, status_msg
                now = datetime.now()

                # Check if enough time has passed since last update
                if (now - last_update_time).seconds < update_interval:
                    return

                last_update_time = now
                diff = (now - start_time).seconds
                speed = current / diff if diff > 0 else 0
                percentage = current * 100 / total

                # Calculate ETA
                if speed > 0:
                    eta = (total - current) / speed
                    eta_hours = int(eta // 3600)
                    eta_minutes = int((eta % 3600) // 60)
                    eta_seconds = int(eta % 60)
                else:
                    eta_hours = eta_minutes = eta_seconds = 0

                # Calculate elapsed time
                elapsed_minutes = diff // 60
                elapsed_seconds = diff % 60

                # Create progress bar
                bar_length = 10
                filled_length = int(percentage / 100 * bar_length)
                bar = '[' + '■' * filled_length + '□' * (bar_length - filled_length) + ']'

                # Format progress text
                progress_text = (
                    f"Progress: {bar} {percentage:.1f}%\n"
                    f"📥 Uploading: {humanbytes(current)} | {humanbytes(total)}\n"
                    f"⚡️ Speed: {humanbytes(speed)}/s\n"
                    f"⌛ ETA: {eta_hours}h {eta_minutes}m {eta_seconds}s\n"
                    f"⏱️ Time elapsed: {elapsed_minutes}m {elapsed_seconds}s"
                )

                # Update messages with progress
                if channel_msg:
                    channel_msg = await safe_edit_message(channel_msg, progress_text)
                if status_msg:
                    status_msg = await safe_edit_message(status_msg, progress_text)

            except Exception as e:
                if "420 FLOOD_WAIT" not in str(e):
                    logger.error(f"Progress update failed: {str(e)}")

        # Send file with progress
        sent_message = await message.reply_document(
            document=output_file,
            caption=caption,
            thumb=thumbnail,
            progress=progress_callback
        )

        try:
            # Save to DB_CHANNEL and generate link
            db_msg = await sent_message.copy(chat_id=DB_CHANNEL)
            logger.info(f"File saved to DB_CHANNEL: {output_file}")

            link, reply_markup = await generate_link(client, db_msg)
            if link:
                await message.reply_text(
                    f"🔗 Link Generated Successfully!",
                    reply_markup=reply_markup
                )

                # Delete channel progress message and post to main channel
                if channel_msg:
                    try:
                        await channel_msg.delete()
                    except MessageIdInvalid:
                        pass
                await post_to_main_channel(client, new_name, link)

        except Exception as e:
            logger.error(f"Failed to save to DB_CHANNEL or generate link: {e}")

        if status_msg:
            status_msg = await safe_edit_message(status_msg, "✅ Process Complete!")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to merge subtitles: {e}")
        if status_msg:
            status_msg = await safe_edit_message(status_msg, f"❌ Error: {e}")
        if channel_msg:
            try:
                await channel_msg.delete()
            except MessageIdInvalid:
                pass
    except Exception as e:
        logger.error(f"Error in merge_subtitles_task: {e}")
        if status_msg:
            status_msg = await safe_edit_message(status_msg, f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        try:
            if os.path.exists("removed_subtitles.mkv"):
                os.remove("removed_subtitles.mkv")
            cleanup(user_id)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")