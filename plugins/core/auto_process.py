import os, time
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.ffmpeg import run_cmd
from plugins.core.change_sub_format import change_sub_format
from plugins.progressbar import progress_bar
from plugins.cleanup import cleanup_system
from plugins.link_generation import generate_link
from config import OWNER_ID, DOWNLOAD_DIR, FONT, LOGGER, media_obj_store, MAIN_CHANNEL, DB_CHANNEL, ANIME_COVER

log = LOGGER("auto_process.py")

CHANGE_VIDEO_FORMAT_OPT = ["🚫", "ᴍᴋᴠ", "ᴍᴘ4"]
CHANGE_SUB_FORMAT_OPT = ["🚫", "ᴀss", "sʀᴛ"]
POST_OPT = ["🚫", "❇️"]

VIDEO_EXT_MAP = {
    "ᴍᴋᴠ": "mkv",
    "ᴍᴘ4": "mp4",
}

AUTO_PS_STATE = {}
MEDIA_STORE = {}
WAITING_SUB = {}


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
        await q.answer("ɴᴏ ᴍᴇᴅɪᴀ ʟᴏᴀᴅᴇᴅ", show_alert=True)
        return

    get_state(uid)
    MEDIA_STORE.setdefault(uid, {})
    await q.message.edit_text("⚙️ sᴇʟᴇᴄᴛ ᴏᴘᴛɪᴏɴs", reply_markup=build_kb(uid))
    await q.answer()


# ---------- toggles ----------
def kb_callback_data(kb):
    if not kb:
        return None
    return [[btn.callback_data for btn in row] for row in kb.inline_keyboard]

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
        m = await client.send_message(uid, "🏢 sᴇɴᴅ .ᴀss ᴏʀ .sʀᴛ ʜᴇʀᴇ")
        MEDIA_STORE.setdefault(uid, {})["waiting_msg_id"] = m.id

    new_kb = build_kb(uid)
    old_data = kb_callback_data(q.message.reply_markup)
    new_data = kb_callback_data(new_kb)

    if old_data != new_data:
        await q.message.edit_reply_markup(new_kb)

    await q.answer()


# ---------- receive subtitle ----------
@Bot.on_message(filters.user(OWNER_ID) & filters.document)
async def receive_sub(client: Client, msg):
    uid = msg.from_user.id
    if not WAITING_SUB.get(uid):
        return

    doc = msg.document
    if not doc.file_name.lower().endswith((".srt", ".ass")):
        return await msg.reply_text("ᴏɴʟʏ .ᴀss ᴏʀ .sʀᴛ ᴀʟʟᴏᴡᴇᴅ")
 
    try:
        db_msg = await client.copy_message(
            chat_id=DB_CHANNEL,
            from_chat_id=msg.chat.id,
            message_id=msg.id
        )
    except Exception as e:
        log.exception("Failed to copy subtitle to DB channel")
        await msg.reply_text(f"ғᴀɪʟᴇᴅ ᴛᴏ ᴄᴏᴘʏ sᴜʙ ғɪʟᴇ ᴛᴏ ᴅʙ ᴄʜᴀɴɴᴇʟ: {str(e)[:100]}")
        return  # stop processing if copy fails

    status = await msg.reply_text("ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙ...")
    start = time.time()

    if db_msg:
        sub_path = await msg.download(
            os.path.join(DOWNLOAD_DIR, doc.file_name),
            progress=progress_bar,
            progress_args=(start, status, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ sᴜʙᴛɪᴛʟᴇ..")
        )

        MEDIA_STORE.setdefault(uid, {})["sub_path"] = sub_path
        WAITING_SUB[uid] = False

        # delete progress/sub messages
        await status.delete()
        await msg.delete()


# ---------- confirm & process ----------
@Bot.on_callback_query(filters.regex("^confirm$") & filters.user(OWNER_ID))
async def confirm_and_run(client: Client, q: CallbackQuery):
    status = None
    uid = q.from_user.id
    state = get_state(uid)
    client_obj = client  # use the client instance itself for filename/episode
    msg_obj = media_obj_store.get(uid)
    if not msg_obj:
        return await q.answer("ɴᴏ ᴍᴇᴅɪᴀ ʟᴏᴀᴅᴇᴅ", show_alert=True)

    status = await q.message.edit_text("⏳ ᴘʀᴏᴄᴇsssɪɴɢ..")
    tmp_files = []

    try:
        # --- download video ---
        start = time.time()
        video_path = await msg_obj.download(
            progress=progress_bar,
            progress_args=(start, status, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴠɪᴅᴇᴏ...")
        )
        tmp_files.append(video_path)

        # --- convert video format ---
        ui = CHANGE_VIDEO_FORMAT_OPT[state["video"]]
        cur_ext = os.path.splitext(video_path)[1].lstrip(".").lower()
        tgt_ext = VIDEO_EXT_MAP.get(ui, cur_ext)
        if ui != "🚫" and cur_ext != tgt_ext:
            out_path = os.path.splitext(video_path)[0] + f".{tgt_ext}"
            await run_cmd(["ffmpeg", "-i", video_path, "-c", "copy", out_path])
            video_path = out_path
            tmp_files.append(out_path)

        # --- final output filename ---
        final_name = client.filename.format(episode=client.episode)
        final_path = os.path.join(DOWNLOAD_DIR, final_name)

        # --- handle subtitle ---
        sub_path = MEDIA_STORE.get(uid, {}).get("sub_path")
        if sub_path:
            tmp_files.append(sub_path)
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", sub_path,
                "-attach", FONT,
                "-metadata:s:t", "mimetype=application/x-truetype-font",
                "-map", "0", "-map", "1",
                "-c", "copy",
                # --- container-level metadata ---
                "-metadata", 'title=HeavenlySubs',
                "-metadata", 'author=https://t.me/HeavenlySubs',
                "-metadata", 'comment=HeavenlySubs',
                "-metadata", 'description=HeavenlySubs | OnlyNoco',
                "-metadata", 'encoded_by=HeavenlySubsBot v2.213',
                "-metadata", 'copyright=© 2025 ~ OnlyNoco | HeavenlySubs',
                "-metadata", 'genre=Dongwha',
                "-metadata", 'year=2025',
                # --- subtitle-level metadata ---
                "-metadata:s:s:0", "title=HeavenlySubs Softsub",
                "-metadata:s:s:0", "language=eng",
                "-disposition:s:0", "default",
                final_path
            ]
            
            await run_cmd(cmd)
            video_path = final_path
            tmp_files.append(final_path)

        MEDIA_STORE.setdefault(uid, {})["output_path"] = video_path
        await status.edit_text(f"ᴅᴏɴᴇ {os.path.basename(video_path)}")

        # --- POST TEMPLATE ---
        post_selection = POST_OPT[state["post"]]
        output_path = MEDIA_STORE[uid]["output_path"]
        
        if post_selection == "❇️":
            # --- Upload to database channel & generate link ---
            try:
                
                thumb_path = await client.download_media(client.thumb)

                db_msg = await client.send_document(
                    DB_CHANNEL,
                    output_path,
                    thumb=thumb_path,
                    caption=None,
                    progress=progress_bar,
                    progress_args=(time.time(), status, "ᴜᴘʟᴏᴀᴅɪɴɢ ᴛᴏ ᴅʙ ᴄʜᴀɴɴᴇʟ...")
                )
                
                # generate link
                try:
                    file_link, keyboard = await generate_link(client, db_msg)
                except Exception as e:
                    log.exception("Link generation failed")
                    await status.edit_text(f"ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ: {str(e)[:100]}")
                    return  # skip posting if link fails
                
                caption = (
                    f"**☗   Battle Through The Heavens**\n\n"
                    f"**⦿   Ratings: 9.8**\n"
                    f"**⦿   Status: Airing**\n"
                    f"**⦿   Episode: `{client.episode}`**\n" 
                    f"**⦿   Subtitle: `English`**\n" 
                    f"**⦿   Quality: 720p**\n"
                    f"**⦿   Genres: `Action`, `Adventure`, `Harem`, `Romance`, `Cultivation`**\n\n"
                    f"**◆   Synopsis: __In a land where no magic is present. A land where the strong make the rules and weak have to obey...[Read More](https://myanimelist.net/anime/36491/Doupo_Cangqiong)__**\n"
                )
                
                '''keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ ‹› ᴡᴀᴛᴄʜ •", url=file_link)]]
                )'''

                await client.send_photo(
                    MAIN_CHANNEL,
                    photo=ANIME_COVER,
                    caption=caption,
                    reply_markup=keyboard
                )

            except Exception as e:
                log.exception("Failed to post via DB channel")
                await status.edit_text(f"ᴜᴘʟᴏᴀᴅ ᴛᴏ ᴅʙ ᴄʜᴀɴɴᴇʟ ғᴀɪʟᴇᴅ: {str(e)[:100]}")
        
        elif post_selection == "🚫":
            # --- Direct PM to user ---
            try:

                thumb_path = await client.download_media(client.thumb)

                await client.send_document(
                    uid,  # send to owner
                    output_path,
                    thumb=thumb_path,
                    caption=os.path.basename(output_path),
                    progress=progress_bar,
                    progress_args=(time.time(), None, "ᴜᴘʟᴏᴀᴅɪɴɢ...")
                )
            except Exception as e:
                log.exception("Failed to send PM to user")
                await status.edit_text(f"ᴜᴘʟᴏᴀᴅ ғᴀɪʟᴇᴅ: {str(e)[:100]}")
            

    except Exception as e:
        log.exception("auto process failed")
        await status.edit_text(f"ᴍᴀɪɴ ᴇʀʀᴏʀ:{str(e)}")

    finally:
        # cleanup temp files (except final output)
        to_remove = [f for f in tmp_files if f != MEDIA_STORE.get(uid, {}).get("output_path")]
        await cleanup_system(None, uid, to_remove)

        # clear memory for this user
        MEDIA_STORE.pop(uid, None)
        AUTO_PS_STATE.pop(uid, None)
        WAITING_SUB.pop(uid, None)