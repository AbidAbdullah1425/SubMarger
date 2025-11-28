from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery, 
    ForceReply,
    Message
)
from pyrogram.enums import ParseMode
from bot import Bot 
from config import OWNER_ID
from database.database import MongoDB # ❗ FIXED: Changed to class import

# --- STATE MANAGEMENT DICTIONARY ---
# {chat_id: prompt_message_id}
WAITING_FOR_INPUT = {}

# --- Helper to get context ---
async def get_settings_context(event):
    """Determines chat_id, the message object, and user_id."""
    if isinstance(event, CallbackQuery):
        return event.message.chat.id, event.message, event.from_user.id
    return event.chat.id, event, event.from_user.id

# ------------------------------------------------------------------
# 1. INPUT HANDLER (Listener for ALL Replies - Core Logic)
# ------------------------------------------------------------------
# ❗ FIXED: Removed '& ~filters.edited' to resolve AttributeError
@Bot.on_message(filters.text & filters.private & filters.user(OWNER_ID), group=1)
async def process_user_input_force_reply(client: Client, message: Message):
    chat_id = message.chat.id
    
    # Optional: Check if the message has been edited. If so, ignore it.
    if message.edit_date:
        return

    # 1. Check if the user is currently expected to provide input
    if chat_id in WAITING_FOR_INPUT:
        prompt_id = WAITING_FOR_INPUT.pop(chat_id)
        
        try:
            # 2. Crucial Check: Ensure the message is a reply to the specific prompt
            if message.reply_to_message and message.reply_to_message.id == prompt_id:
                
                prompt_msg = await client.get_messages(chat_id, prompt_id)
                
                # --- FILENAME PROCESSING ---
                if "ғɪʟᴇɴᴀᴍᴇ" in prompt_msg.text: 
                    fmt = message.text.strip()
                    
                    # ❗ Placeholder for DB update using MongoDB class
                    # You need to implement the actual method on MongoDB class here
                    # Example: await MongoDB().update_settings(chat_id, "filename", fmt)
                    # Assuming a function called update_settings for now, but you should adjust.
                    await update_settings_placeholder(chat_id, "filename", fmt)
                    
                    # --- CLEAN VISUAL FLOW ---
                    await prompt_msg.delete() 
                    await message.delete()   
                    
                    await client.send_message(
                        chat_id,
                        f"<b>✅ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ᴜᴘᴅᴀᴛᴇᴅ</b>\n<code>{fmt}</code>",
                        parse_mode=ParseMode.HTML
                    )
                
                # If it's a thumbnail prompt but they sent text (ignored)
                elif "ᴛʜᴜᴍʙɴᴀɪʟ" in prompt_msg.text:
                    await client.send_message(
                        chat_id, 
                        "<b>⚠️ Pʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ **ᴘʜᴏᴛᴏ** ᴀs ᴀ ʀᴇᴘʟʏ ᴛᴏ sᴇᴛ ᴛʜᴜᴍʙɴᴀɪʟ.</b>",
                        parse_mode=ParseMode.HTML
                    )
                
            else:
                WAITING_FOR_INPUT[chat_id] = prompt_id
                
        except Exception as e:
            print(f"Error processing user input: {e}")
            await client.send_message(chat_id, f"<b>⚠️ Iɴᴛᴇʀɴᴀʟ ᴇʀʀᴏʀ:</b> {e}", parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# 2. SET FILENAME COMMAND (Trigger)
# ------------------------------------------------------------------
@Bot.on_message(filters.command("set_filename") & filters.user(OWNER_ID))
@Bot.on_callback_query(filters.regex("^set_filename$") & filters.user(OWNER_ID))
async def set_filename_force_reply(client: Client, event):
    chat_id, original_msg, user_id = await get_settings_context(event)

    prompt_text = "<b>📝 sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ʜᴇʀᴇ!</b>"

    # Send the prompt with ForceReply UI
    if isinstance(event, CallbackQuery):
        await original_msg.delete()
        ask_msg = await client.send_message(chat_id, prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)
    else:
        ask_msg = await original_msg.reply_text(prompt_text, reply_markup=ForceReply(True), parse_mode=ParseMode.HTML)

    # ❗ Store the message ID for the input handler to check
    WAITING_FOR_INPUT[chat_id] = ask_msg.id


# ------------------------------------------------------------------
# 3. DEDICATED THUMBNAIL PHOTO HANDLER
# ------------------------------------------------------------------
@Bot.on_message(filters.photo & filters.private & filters.user(OWNER_ID), group=2)
async def process_thumbnail_photo_input(client: Client, message: Message):
    chat_id = message.chat.id
    
    if chat_id in WAITING_FOR_INPUT:
        prompt_id = WAITING_FOR_INPUT.pop(chat_id)
        
        try:
            # Check if this photo is a reply to the thumbnail prompt
            if message.reply_to_message and message.reply_to_message.id == prompt_id:
                
                prompt_msg = await client.get_messages(chat_id, prompt_id)
                
                # Check if the prompt text contains "THUMBNAIL"
                if "ᴛʜᴜᴍʙɴᴀɪʟ" in prompt_msg.text: 
                    file_id = message.photo.file_id
                    
                    # ❗ Placeholder for DB update using MongoDB class
                    await update_settings_placeholder(chat_id, "thumb", file_id) 
                    
                    # --- CLEAN VISUAL FLOW ---
                    await prompt_msg.delete() 
                    await message.delete()
                    
                    await client.send_message(
                        chat_id,
                        "<b>✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</b>",
                        parse_mode=ParseMode.HTML
                    )
        except Exception as e:
            print(f"Error processing photo input: {e}")
            await client.send_message(chat_id, f"<b>⚠️ Iɴᴛᴇʀɴᴀʟ ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ ᴘʀᴏᴄᴇSSɪɴɢ:</b> {e}", parse_mode=ParseMode.HTML)

# --- Placeholder function (REPLACE WITH YOUR ACTUAL DB LOGIC) ---
# Since you changed the import to MongoDB, I cannot call a non-existent function.
# You must integrate the logic like: await MongoDB().update_setting(...)
async def update_settings_placeholder(chat_id, key, value):
    # DUMMY FUNCTION - REPLACE ME
    pass