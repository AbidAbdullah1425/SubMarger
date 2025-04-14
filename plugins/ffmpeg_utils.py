import os
import subprocess
import logging
from datetime import datetime
from .video_handler import user_data, logger
from .cleanup import cleanup
from .progress_handler import (
    StatusMessages,
    create_status_messages,
    create_progress_callback,
    update_status_text,
    delete_channel_status
)
from config import DB_CHANNEL, MAIN_CHANNEL
from .link_generation import generate_link
from .channel_post import post_to_main_channel

async def merge_subtitles_task(client, message, user_id):
    data = user_data[user_id]
    video = data["video"]
    subtitle = data["subtitle"]
    new_name = data["new_name"]
    caption = data["caption"]
    output_file = f"{new_name}.mkv"
    font = 'Assist/Font/OathBold.otf'
    thumbnail = 'Assist/Images/thumbnail.jpg'

    try:
        # Initialize status messages
        status_messages = await create_status_messages(client, message, MAIN_CHANNEL)
        if not status_messages:
            return await message.reply("Failed to initialize status messages.")

        # Download video with progress
        start_time = datetime.now()
        download_callback = create_progress_callback(status_messages, start_time, "Downloading Video")
        
        # If video is a message, download it
        if hasattr(video, 'file_id'):
            await update_status_text(status_messages, "Starting Download...")
            video_path = await client.download_media(
                message=video,
                progress=download_callback
            )
            video = video_path if video_path else video

        # Process video (no progress bar needed)
        await update_status_text(status_messages, "Removing Existing Subtitles...")
        remove_subs_cmd = [
            "ffmpeg", "-i", video,
            "-map", "0:v", "-map", "0:a?",
            "-c", "copy", "-y", "removed_subtitles.mkv"
        ]
        subprocess.run(remove_subs_cmd, check=True)

        # Merge subtitles (no progress bar needed)
        await update_status_text(status_messages, "Merging Subtitles...")
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

        # Upload with progress bar
        await update_status_text(status_messages, "Preparing Upload...")
        start_time = datetime.now()
        upload_callback = create_progress_callback(status_messages, start_time, "Uploading Video")
        
        sent_message = await message.reply_document(
            document=output_file,
            caption=caption,
            thumb=thumbnail,
            progress=upload_callback
        )

        # Save to DB_CHANNEL and generate link
        try:
            db_msg = await sent_message.copy(chat_id=DB_CHANNEL)
            link, reply_markup = await generate_link(client, db_msg)
            
            if link:
                await message.reply_text(
                    f"<b>🔗 Shareable Link:</b>\n\n{link}",
                    reply_markup=reply_markup
                )
                # Post to main channel and delete progress message
                await post_to_main_channel(client, new_name, link)
                await delete_channel_status(status_messages.channel)
                await status_messages.pm.edit_text(
                    f"✅ Process Complete!\n"
                    f"⌚ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
                
        except Exception as e:
            logger.error(f"Failed to save to DB_CHANNEL or generate link: {e}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to merge subtitles: {e}")
        if status_messages:
            error_text = (
                f"❌ Error occurred!\n\n"
                f"⌚ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"▫️ Error: {str(e)}"
            )
            await update_status_text(status_messages, error_text)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists("removed_subtitles.mkv"):
            os.remove("removed_subtitles.mkv")
        cleanup(user_id)

# Simple functions without progress bars
async def extract_subtitles(client, message, user_id):
    data = user_data[user_id]
    video_file = data["video"]
    output_subtitle = video_file.rsplit('.', 1)[0] + ".srt"
    output_ass = video_file.rsplit('.', 1)[0] + ".ass"

    status_msg = await message.reply("Extracting subtitles...")
    try:
        subprocess.run(["ffmpeg", "-i", video_file, "-map", "0:s:0", output_subtitle], check=True)
        subprocess.run(["ffmpeg", "-i", output_subtitle, output_ass], check=True)
        
        await message.reply_document(document=output_subtitle, caption="Extracted subtitle file (SRT)")
        await message.reply_document(document=output_ass, caption="Converted subtitle file (ASS)")
        await status_msg.edit("✅ Subtitles extracted and converted successfully!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract subtitles: {e}")
        await status_msg.edit(f"❌ Error: {e}")

async def generate_screenshot(client, message, user_id):
    data = user_data[user_id]
    video_file = data["video"]
    screenshot_path = video_file.rsplit('.', 1)[0] + "_screenshot.png"
    
    status_msg = await message.reply("Generating screenshot...")
    try:
        subprocess.run([
            "ffmpeg", "-ss", "00:03:05", "-i", video_file,
            "-frames:v", "1", "-q:v", "2", screenshot_path
        ], check=True)
        
        await message.reply_photo(photo=screenshot_path, caption="Screenshot generated")
        await status_msg.edit("✅ Screenshot generated!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate screenshot: {e}")
        await status_msg.edit(f"❌ Error: {e}")