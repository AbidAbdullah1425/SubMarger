import os, time
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.start import media_obj_store
from plugins.ffmpeg import run_cmd
from plugins.core.change_sub_format import change_sub_format
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from config import OWNER_ID, DOWNLOAD_DIR, FONT, LOGGER

log = LOGGER("auto_process.py")

# UI options (index cycles)
CHANGE_VIDEO_FORMAT_OPT = ["🚫", "ᴍᴋᴠ", "ᴍᴘ4"]
CHANGE_SUB_FORMAT_OPT   = ["🚫", "ᴀss", "sʀᴛ"]
POST_OPT                = ["🚫", "❇️"]

AUTO_PS_STATE = {}   # {user_id: {"video":0,"sub":0,"post":0}}
MEDIA_STORE   = {}   # {user_id: {"video_path":..., "sub_doc_file_id":..., "output":...}}
WAITING_SUB = {}   # {user_id: True/False}

def get_state(uid):
    if uid not in AUTO_PS_STATE:
        AUTO_PS_STATE[uid] = {"video":0,"sub":0,"post":0}
    return AUTO_PS_STATE[uid]

def build_kb(uid):
    s = get_state(uid)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴄʜᴀɴɢᴇ ᴠɪᴅᴇᴏ ғᴏʀᴍᴀᴛ", callback_data="dummy"),
         InlineKeyboardButton(CHANGE_VIDEO_FORMAT_OPT[s["video"]], callback_data="toggle_video")],
        [InlineKeyboardButton("ᴀᴅᴅ sᴜʙ", callback_data="dummy"),
         InlineKeyboardButton(CHANGE_SUB_FORMAT_OPT[s["sub"]], callback_data="toggle_sub"),
         InlineKeyboardButton("ɢɪᴠᴇ sᴜʙ", callback_data="give_file")],
        [InlineKeyboardButton("ᴘᴏsᴛ", callback_data="dummy"),
         InlineKeyboardButton(POST_OPT[s["post"]], callback_data="toggle_post")],
        [InlineKeyboardButton("ᴄᴏɴғɪʀᴍ", callback_data="confirm")]
    ])

@Bot.on_callback_query(filters.regex("^auto_process$") & filters.user(OWNER_ID))
async def show_auto_process(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    # require media in memory
    if uid not in media_obj_store:
        await q.answer("Nᴏ ᴍᴇᴅɪᴀ ʟᴏᴀᴅᴇᴅ!", show_alert=True)
        return await q.message.edit_text("! ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ᴏɴ ᴛʜᴇ ᴍᴇᴍᴏʀʏ.")
    get_state(uid)            # ensure state exists
    MEDIA_STORE.setdefault(uid, {})  # ensure store
    await q.message.edit_text("⚙️ sᴇʟᴇᴄᴛ ᴏᴘᴛɪᴏɴs ᴀɴᴅ ᴘʀᴏᴄᴇᴇᴅ", reply_markup=build_kb(uid))
    await q.answer()

# toggles
@Bot.on_callback_query(filters.regex("^(toggle_video|toggle_sub|toggle_post)$") & filters.user(OWNER_ID))
async def toggle_cb(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    s = get_state(uid)
    if q.data == "toggle_video":
        s["video"] = (s["video"] + 1) % len(CHANGE_VIDEO_FORMAT_OPT)
        await q.answer(f"Video: {CHANGE_VIDEO_FORMAT_OPT[s['video']]}")
    elif q.data == "toggle_sub":
        s["sub"] = (s["sub"] + 1) % len(CHANGE_SUB_FORMAT_OPT)
        await q.answer(f"Subtitle: {CHANGE_SUB_FORMAT_OPT[s['sub']]}")
    elif q.data == "toggle_post":
        s["post"] = (s["post"] + 1) % len(POST_OPT)
        await q.answer(f"Post: {POST_OPT[s['post']]}")
    await q.message.edit_reply_markup(build_kb(uid))

# give file (ForceReply path handled elsewhere) -- we use a status msg approach
@Bot.on_callback_query(filters.regex("^give_file$") & filters.user(OWNER_ID))
async def give_file_prompt(client: Client, q: CallbackQuery):
    uid = q.from_user.id

    # enable waiting mode
    WAITING_SUB[uid] = True

    # send fresh status message
    status = await client.send_message(
        uid,
        "🏢 Reply with a .srt or .ass subtitle file"
    )

    # store this status msg id so we can delete it later
    MEDIA_STORE.setdefault(uid, {})["waiting_msg_id"] = status.message_id

    await q.answer("Send subtitle now.")
    

# handle incoming reply subtitle
@Bot.on_message(filters.user(OWNER_ID) & filters.reply)
async def receive_sub(client: Client, msg):
    uid = msg.from_user.id
    store = MEDIA_STORE.get(uid)
    if not store or "waiting_status_msg" not in store:
        return
    if not msg.reply_to_message or msg.reply_to_message.message_id != store["waiting_status_msg"]:
        return
    # accept document only
    doc = msg.document
    if not doc or not doc.file_name.lower().endswith((".srt", ".ass")):
        await msg.reply("sᴇɴᴅ .ᴀss ᴏʀ .sʀᴛ ᴅᴏᴄᴜᴍᴇɴᴛ ғɪʟᴇ")
        return
    # download subtitle to DOWNLOAD_DIR
    start = time.time()
    sub_path = await msg.download(file_name=os.path.join(DOWNLOAD_DIR, doc.file_name),
                                  progress=progress_bar, progress_args=(start, msg, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ..."))
    # save path and delete original user msg + status
    store["sub_path"] = sub_path
    try:
        await client.delete_messages(uid, store["waiting_status_msg"])
        await msg.delete()
    except:
        pass
    await client.send_message(uid, f"sᴜʙᴛɪᴛʟᴇ sᴀᴠᴇᴅ {os.path.basename(sub_path)}")

# Confirm -> run pipeline
@Bot.on_callback_query(filters.regex("^confirm$") & filters.user(OWNER_ID))
async def confirm_and_run(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    state = get_state(uid)
    if uid not in media_obj_store:
        await q.answer("ɴᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ", show_alert=True); return
    msg_obj = media_obj_store[uid]

    status = await q.message.edit_text("ᴘʀᴏᴄᴇssɪɴɢ...")  # single status msg

    tmp_files = []
    try:
        # 1) ensure video downloaded
        video_path = getattr(msg_obj, "downloaded_file", None)
        if not video_path or not os.path.exists(video_path):
            start = time.time()
            video_name = f"{int(time.time())}_{msg_obj.document.file_name if msg_obj.document else 'video'}"
            video_path = os.path.join(DOWNLOAD_DIR, video_name)
            video_path = await msg_obj.download(file_name=video_path,
                                                progress=progress_bar,
                                                progress_args=(start, q.message, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ..."))
            msg_obj.downloaded_file = video_path
        tmp_files.append(video_path)

        # 2) change video format if selected
        target_video = CHANGE_VIDEO_FORMAT_OPT[state["video"]]
        if target_video != "🚫":
            out_video = os.path.splitext(video_path)[0] + f".{target_video}"
            # simple remux (copy) like your change_video_format module
            await q.message.edit_text(f"ᴄᴏɴᴠᴇʀᴛɪɴɢ ᴠɪᴅᴇᴏ ᴛᴏ {target_video} ...")
            success, rc, out, err = await run_cmd(["ffmpeg", "-i", video_path, "-c", "copy", out_video])
            if not success or not os.path.exists(out_video):
                raise RuntimeError(f"ᴠɪᴅᴇᴏ ᴄᴏɴᴠᴇʀᴛɪᴏɴ ғᴀɪʟᴇᴅ: {err}")
            video_path = out_video
            tmp_files.append(out_video)

        # 3) subtitle: if user provided and requested to be converted to specific type
        sub_path = MEDIA_STORE.get(uid, {}).get("sub_path")
        target_sub = CHANGE_SUB_FORMAT_OPT[state["sub"]]
        if sub_path and target_sub != "🚫":
            # convert sub to target_sub if needed
            cur_ext = os.path.splitext(sub_path)[1].lower().lstrip(".")
            if cur_ext != target_sub:
                await q.message.edit_text(f"ᴄᴏɴᴠᴇʀᴛɪɴɢ sᴜʙᴛɪᴛʟᴇ ᴛᴏ {target_sub} ...")
                new_sub = await change_sub_format(sub_path, target_sub, DOWNLOAD_DIR)
                if not os.path.exists(new_sub):
                    raise RuntimeError("sᴜʙᴛɪᴛʟᴇ ᴄᴏɴᴠᴇʀᴛɪᴏɴ ғᴀɪʟᴇᴅ")
                sub_path = new_sub
                tmp_files.append(sub_path)
        # 4) attach subtitle if we have sub_path (ass or srt) -> produce final output
        if sub_path:
            out_final = os.path.splitext(video_path)[0] + ".final" + os.path.splitext(video_path)[1]
            await q.message.edit_text("🔗 ᴀᴅᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ ᴛᴏ ᴠɪᴅᴇᴏ...")
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
                out_final
            ]
            success, rc, out, err = await run_cmd(cmd)
            if not success or not os.path.exists(out_final):
                raise RuntimeError(f"ᴀᴅᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ ᴛᴏ ᴠᴜᴅᴇᴏ ғᴀɪʟᴇᴅ: {err}")
            video_path = out_final
            tmp_files.append(out_final)

        # save output path to MEDIA_STORE
        MEDIA_STORE.setdefault(uid, {})["output_path"] = video_path

        await q.message.edit_text(f"ᴅᴏɴᴇ ᴏᴜᴛᴘᴜᴛ: {os.path.basename(video_path)}")

    except Exception as e:
        log.exception("ᴀᴜᴛᴏ ᴘʀᴏᴄᴇss ғᴀɪʟᴇᴅ")
        await q.message.edit_text(f"ᴇʀʀᴏʀ: {e}")

    finally:
        # cleanup temp files (keep output)
        to_remove = [f for f in tmp_files if f != MEDIA_STORE.get(uid, {}).get("output_path")]
        await cleanup_system(None, uid, to_remove)