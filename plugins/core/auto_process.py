import os, time
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.ffmpeg import run_cmd
from plugins.core.change_sub_format import change_sub_format
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from config import OWNER_ID, DOWNLOAD_DIR, FONT, LOGGER, media_obj_store

log = LOGGER("auto_process.py")

CHANGE_VIDEO_FORMAT_OPT = ["🚫", "ᴍᴋᴠ", "ᴍᴘ4"]
CHANGE_SUB_FORMAT_OPT   = ["🚫", "ᴀss", "sʀᴛ"]
POST_OPT = ["🚫", "❇️"]

VIDEO_EXT_MAP = {
    "ᴍᴋᴠ": "mkv",
    "ᴍᴘ4": "mp4",
}

AUTO_PS_STATE = {}
MEDIA_STORE   = {}
WAITING_SUB   = {}


# ---------- helpers ----------
def get_state(uid):
    return AUTO_PS_STATE.setdefault(uid, {"video": 0, "sub": 0, "post": 0})


def build_kb(uid):
    s = get_state(uid)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴄʜᴀɴɢᴇ ᴠɪᴅᴇᴏ ғᴏʀᴍᴀᴛ", callback_data="dummy"),
         InlineKeyboardButton(CHANGE_VIDEO_FORMAT_OPT[s["video"]], callback_data="toggle_video")],
        [InlineKeyboardButton("ᴀᴅᴅ sᴜʙ", callback_data="dummy"),
         InlineKeyboardButton(CHANGE_SUB_FORMAT_OPT[s["sub"]], callback_data="toggle_sub"),
         InlineKeyboardButton("ɢɪᴠᴇ sᴜʙ", callback_data="set_waiting_sub")],
        [InlineKeyboardButton("ᴘᴏsᴛ", callback_data="dummy"),
         InlineKeyboardButton(POST_OPT[s["post"]], callback_data="toggle_post")],
        [InlineKeyboardButton("ᴄᴏɴғɪʀᴍ", callback_data="confirm")]
    ])


# ---------- menu ----------
@Bot.on_callback_query(filters.regex("^auto_process$") & filters.user(OWNER_ID))
async def show_auto_process(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    if uid not in media_obj_store:
        await q.answer("No media loaded", show_alert=True)
        return

    get_state(uid)
    MEDIA_STORE.setdefault(uid, {})
    await q.message.edit_text("⚙️ Select options", reply_markup=build_kb(uid))
    await q.answer()


# ---------- toggles ----------
@Bot.on_callback_query(filters.regex("^(toggle_video|toggle_sub|toggle_post|set_waiting_sub)$") & filters.user(OWNER_ID))
async def toggle_cb(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    s = get_state(uid)

    if q.data == "toggle_video":
        s["video"] = (s["video"] + 1) % len(CHANGE_VIDEO_FORMAT_OPT)
    elif q.data == "toggle_sub":
        s["sub"] = (s["sub"] + 1) % len(CHANGE_SUB_FORMAT_OPT)
    elif q.data == "toggle_post":
        s["post"] = (s["post"] + 1) % len(POST_OPT)
    elif q.data == "set_waiting_sub":
        WAITING_SUB[uid] = True
        m = await client.send_message(uid, "🏢 Send .ass or .srt")
        MEDIA_STORE.setdefault(uid, {})["waiting_msg_id"] = m.id

    await q.message.edit_reply_markup(build_kb(uid))
    await q.answer()


# ---------- receive subtitle ----------
@Bot.on_message(filters.user(OWNER_ID) & filters.document)
async def receive_sub(client: Client, msg):
    uid = msg.from_user.id
    if not WAITING_SUB.get(uid):
        return

    doc = msg.document
    if not doc.file_name.lower().endswith((".srt", ".ass")):
        return await msg.reply_text("Send .ass or .srt only")

    status = await msg.reply_text("⬇️ Downloading subtitle...")
    start = time.time()

    sub_path = await msg.download(
        os.path.join(DOWNLOAD_DIR, doc.file_name),
        progress=progress_bar,
        progress_args=(start, status, "Downloading subtitle")
    )

    MEDIA_STORE.setdefault(uid, {})["sub_path"] = sub_path
    WAITING_SUB[uid] = False

    await status.delete()
    await msg.delete()
    await client.send_message(uid, f"✅ Subtitle saved: {os.path.basename(sub_path)}")


# ---------- confirm ----------
@Bot.on_callback_query(filters.regex("^confirm$") & filters.user(OWNER_ID))
async def confirm_and_run(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    state = get_state(uid)

    msg_obj = media_obj_store.get(uid)
    if not msg_obj:
        return await q.answer("No media", show_alert=True)

    status = await q.message.edit_text("⏳ Processing...")
    tmp_files = []

    try:
        # download video
        start = time.time()
        video_path = await msg_obj.download(
            progress=progress_bar,
            progress_args=(start, status, "Downloading video")
        )
        tmp_files.append(video_path)

        # convert video
        ui = CHANGE_VIDEO_FORMAT_OPT[state["video"]]
        if ui != "🚫":
            cur = os.path.splitext(video_path)[1].lstrip(".").lower()
            tgt = VIDEO_EXT_MAP[ui]
            if cur != tgt:
                out = os.path.splitext(video_path)[0] + f".{tgt}"
                await run_cmd(["ffmpeg", "-i", video_path, "-c", "copy", out])
                video_path = out
                tmp_files.append(out)

        # subtitle
        sub_path = MEDIA_STORE.get(uid, {}).get("sub_path")
        if sub_path:
            out = os.path.splitext(video_path)[0] + ".final" + os.path.splitext(video_path)[1]
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", sub_path,
                "-attach", FONT,
                "-metadata:s:t", "mimetype=application/x-truetype-font",
                "-map", "0", "-map", "1",
                "-c", "copy",
                "-metadata:s:s:0", "language=eng",
                "-disposition:s", "default",
                out
            ]
            await run_cmd(cmd)
            video_path = out
            tmp_files.append(out)

        MEDIA_STORE.setdefault(uid, {})["output_path"] = video_path
        await status.edit_text(f"✅ Done: {os.path.basename(video_path)}")

    except Exception as e:
        log.exception("auto process failed")
        await status.edit_text(str(e))

    finally:
        await cleanup_system(None, uid, tmp_files)