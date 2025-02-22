import os
import subprocess
import logging
from pyrogram import filters
from asyncio import create_task
from bot import Bot
from config import OWNER_ID, LOG_FILE_NAME  

# Temporary storage for user progress and file paths
user_data = {}

# Configure logging
logging.basicConfig(level=logging.INFO)

@Bot.on_message(filters.user(OWNER_ID) & filters.command("start"), group=0)
async def start(client, message):
    await message.reply("Welcome! Send me a video file (MKV or MP4) to add subtitles.")

@Bot.on_message(filters.user(OWNER_ID) & filters.command("logs"), group=0)
async def fetch_logs(client, message):
    try:
        await message.reply_document(LOG_FILE_NAME, caption="Here are the latest logs.")
    except Exception as e:
        await message.reply(f"Error fetching logs: {str(e)}")


# Video Upload Handler
@Bot.on_message(
    filters.user(OWNER_ID) &
    (filters.video | (filters.document & filters.create(lambda _, __, m: m.document and m.document.file_name.endswith((".mkv", ".mp4")))))
)
async def handle_video(client, message):
    user_id = message.from_user.id
    file_name = message.video.file_name if message.video else message.document.file_name
    file_size = message.video.file_size if message.video else message.document.file_size

    logging.info(f"Receiving video: {file_name} ({file_size / (1024*1024):.2f} MB) from {user_id}")

    async def progress_log(current, total):
        percent = (current / total) * 100
        logging.info(f"Downloading: {current / (1024*1024):.2f}/{total / (1024*1024):.2f} MB ({percent:.2f}%) for user {user_id}")

    video_file = await message.download(progress=progress_log)

    if video_file.endswith(".mp4"):
        new_video_file = video_file.replace(".mp4", ".mkv")
        ffmpeg_cmd = ["ffmpeg", "-i", video_file, "-c", "copy", new_video_file]
        subprocess.run(ffmpeg_cmd, check=True)
        os.remove(video_file)
        video_file = new_video_file

    logging.info(f"Download complete: {video_file}")

    user_data[user_id] = {"video": video_file, "step": "video"}
    await message.reply("Video received! Now send the subtitle file (.ass or .srt).")

# Subtitle Upload Handler
@Bot.on_message(
    filters.user(OWNER_ID) &
    filters.document & filters.create(lambda _, __, m: m.document and m.document.file_name.endswith((".ass", ".srt")))
)
async def handle_subtitle(client, message):
    user_id = message.from_user.id

    logging.info(f"Receiving subtitle from {user_id}")

    if user_id in user_data and user_data[user_id].get("step") == "video":
        async def progress_log(current, total):
            percent = (current / total) * 100
            logging.info(f"Downloading subtitle: {percent:.2f}% for user {user_id}")

        subtitle_file = await message.download(progress=progress_log)

        logging.info(f"Subtitle downloaded: {subtitle_file}")

        user_data[user_id]["subtitle"] = subtitle_file
        user_data[user_id]["step"] = "subtitle"
        await message.reply("Subtitle received! Now send the new name for the output file (without extension).")
    else:
        await message.reply("Please send a video file first.")

# Handle Filename & Caption
@Bot.on_message(filters.user(OWNER_ID) & filters.text)
async def handle_name_or_caption(client, message):
    user_id = message.from_user.id

    logging.info(f"Receiving new filename from {user_id}")

    if user_id in user_data and user_data[user_id].get("step") == "subtitle":
        new_name = message.text.strip()

        user_data[user_id]["new_name"] = new_name
        user_data[user_id]["caption"] = new_name
        user_data[user_id]["step"] = "name"
        await message.reply("New name and caption received! Now send a thumbnail image (JPG or PNG).")
    else:
        await message.reply("Please start by sending a video file.")

# Thumbnail Upload Handler
@Bot.on_message(filters.user(OWNER_ID) & filters.photo)
async def handle_thumbnail(client, message):
    user_id = message.from_user.id

    logging.info(f"Receiving thumbnail from {user_id}")

    if user_id in user_data and user_data[user_id].get("step") == "name":
        async def progress_log(current, total):
            percent = (current / total) * 100
            logging.info(f"Downloading thumbnail: {percent:.2f}% for user {user_id}")

        thumbnail_file = await message.download(progress=progress_log)

        logging.info(f"Thumbnail downloaded: {thumbnail_file}")

        user_data[user_id]["thumbnail"] = thumbnail_file

        await message.reply("Thumbnail received! Merging subtitles into the video...")
        create_task(merge_subtitles_task(client, message, user_id))
    else:
        await message.reply("Please send a name first.")

# Merging Subtitles
async def merge_subtitles_task(client, message, user_id):
    data = user_data[user_id]
    video = data["video"]
    subtitle = data["subtitle"]
    new_name = data["new_name"]
    caption = data["caption"]
    thumbnail = data["thumbnail"]
    output_file = f"{new_name}.mkv"

    font = 'Assist/Font/OathBold.otf'

    ffmpeg_cmd = [
        "ffmpeg", "-i", video, "-i", subtitle,
        "-attach", font, "-metadata:s:t:0", "mimetype=application/x-font-otf",
        "-map", "0", "-map", "1",
        "-metadata:s:s:0", "title=DonghuaWillow",
        "-metadata:s:s:0", "language=eng", "-disposition:s:s:0", "default",
        "-c", "copy", output_file
    ]

    try:
        logging.info(f"Merging subtitles for user {user_id}: {output_file}")
        subprocess.run(ffmpeg_cmd, check=True)

        async def upload_progress(current, total):
            percent = (current / total) * 100
            logging.info(f"Uploading: {current / (1024*1024):.2f}/{total / (1024*1024):.2f} MB ({percent:.2f}%) for user {user_id}")

        logging.info(f"Uploading merged video: {output_file}")
        await message.reply_document(
            document=output_file,
            caption=caption,
            thumb=thumbnail,
            progress=upload_progress
        )

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to merge subtitles: {e}")
        await message.reply(f"Error: {e}")

    finally:
        os.remove(video)
        os.remove(subtitle)
        os.remove(thumbnail)
        if os.path.exists(output_file):
            os.remove(output_file)
        user_data.pop(user_id, None)
