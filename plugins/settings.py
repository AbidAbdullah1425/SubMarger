from pyrogram import Client, filters
from bot import Bot 
from pyrogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ForceReply, # ❗ FIXED: Imported ForceReply
    Message
)
from pyrogram.enums import ParseMode
import asyncio
from config import OWNER_ID
from database.database import MongoDB
# --- Helper to get context for messages/callbacks ---
async def get_settings_context(event):
    """Determines chat_id, the message object (to reply/edit), and user_id."""
    if isinstance(event, CallbackQuery):
        # Callback Queries are attached to event.message
        return event.message.chat.id, event.message, event.from_user.id
    # Messages (commands) are the event itself
    return event.chat.id, event, event.from_user.id

# ------------------------------------------------------------------
#                       SET THUMBNAIL (/set_thumb)
# ------------------------------------------------------------------
@Bot.on_message(filters.command("set_thumb") & filters.user(OWNER_ID))
@Bot.on_callback_query(filters.regex("^set_thumb$") & filters.user(OWNER_ID))
async def set_thumbnail(client: Client, event):
    chat_id, original_msg, user_id = await get_settings_context(event)

    prompt_text = (
        "<b>🖼 sᴇɴᴅ ᴏʀ ᴜᴘʟᴏᴀᴅ ᴛʜᴇ ᴛʜᴜᴍʙɴᴀɪʟ ᴅɪʀᴇᴄᴛʟʏ ʜᴇʀᴇ!</b>\n"
        "<code>ᴛɪᴍᴇᴏᴜᴛ: 5 ᴍɪɴs | ᴛʏᴘᴇ /cancel ᴛᴏ sᴛᴏᴘ</code>"
    )
    
    # Send the prompt with ForceReply UI
    if isinstance(event, CallbackQuery):
        await original_msg.delete() # Clean up old menu
        ask_msg = await client.send_message(chat_id, prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)
    else:
        ask_msg = await original_msg.reply_text(prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)

    try:
        # Wait for the user's response
        reply = await client.wait_for_message(
            chat_id=chat_id,
            filters=(filters.photo | filters.text) & filters.user(user_id),
            timeout=300
        )

        # 1. Check for Cancel Command
        if reply.text and reply.text.lower() == "/cancel":
            await ask_msg.delete()
            await reply.delete()
            await client.send_message(chat_id, "<b>❌ Pʀᴏᴄᴇss Cᴀɴᴄᴇʟʟᴇᴅ.</b>", parse_mode=ParseMode.HTML)
            return

        # 2. Process Photo (Success Flow)
        if reply.photo:
            file_id = reply.photo.file_id
            
            # ❗ FIXED: Using the imported DB function
            await update_settings(chat_id, "thumb", file_id) 
            
            # --- CLEAN VISUAL FLOW ---
            await ask_msg.delete() # Delete the bot's prompt
            await reply.delete()   # Delete the user's reply (clean up)
            
            await client.send_message(
                chat_id,
                "<b>✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            # Handle invalid input
            await ask_msg.delete()
            await reply.delete()
            await client.send_message(chat_id, "<b>❌ Iɴᴠᴀʟɪᴅ. Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴘʜᴏᴛᴏ.</b>", parse_mode=ParseMode.HTML)

    except asyncio.TimeoutError:
        # 3. Timeout Handler
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛʀʏ ᴀɢᴀɪɴ •", callback_data="set_thumb")]
        ])
        await ask_msg.edit_text(
            "<b>⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</b>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )

# ------------------------------------------------------------------
#                       SET FILENAME (/set_filename)
# ------------------------------------------------------------------
@Bot.on_message(filters.command("set_filename") & filters.user(OWNER_ID))
@Bot.on_callback_query(filters.regex("^set_filename$") & filters.user(OWNER_ID))
async def set_filename(client: Client, event):
    chat_id, original_msg, user_id = await get_settings_context(event)

    prompt_text = (
        "<b>📝 sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ʜᴇʀᴇ!</b>\n"
        "<code>ᴛɪᴍᴇᴏᴜᴛ: 5 ᴍɪɴs | ᴛʏᴘᴇ /cancel ᴛᴏ sᴛᴏᴘ</code>"
    )

    # Send the prompt with ForceReply UI
    if isinstance(event, CallbackQuery):
        await original_msg.delete()
        ask_msg = await client.send_message(chat_id, prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)
    else:
        ask_msg = await original_msg.reply_text(prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)

    try:
        reply = await client.wait_for_message(
            chat_id=chat_id,
            filters=filters.text & filters.user(user_id),
            timeout=300
        )

        # 1. Check for Cancel Command
        if reply.text.lower() == "/cancel":
            await ask_msg.delete()
            await reply.delete()
            await client.send_message(chat_id, "<b>❌ Pʀᴏᴄᴇss Cᴀɴᴄᴇʟʟᴇᴅ.</b>", parse_mode=ParseMode.HTML)
            return

        # 2. Process Filename (Success Flow)
        fmt = reply.text.strip()
        
        # ❗ FIXED: Using the imported DB function
        await update_settings(chat_id, "filename", fmt)

        # --- CLEAN VISUAL FLOW ---
        await ask_msg.delete() # Delete the bot's prompt
        await reply.delete()   # Delete the user's reply (clean up)
        
        await client.send_message(
            chat_id,
            f"<b>✅ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ᴜᴘᴅᴀᴛᴇᴅ</b>\n<code>{fmt}</code>",
            parse_mode=ParseMode.HTML
        )

    except asyncio.TimeoutError:
        # 3. Timeout Handler
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛʀʏ ᴀɢᴀɪɴ •", callback_data="set_filename")]
        ])
        await ask_msg.edit_text(
            "<b>⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</b>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )