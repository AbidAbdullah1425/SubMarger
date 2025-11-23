from pyrogram import Client, filters  
from bot import Bot 
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import asyncio
from config import OWNER_ID
from database.database import update_settings

@Bot.on_message(filters.command("set_thumb") & filters.user(OWNER_ID))
@Bot.on_callback_query(filters.regex("^set_thumb$") & filters.user(OWNER_ID))
async def set_thumbnail(client: Client, event):
    is_callback = isinstance(event, CallbackQuery)
    user = event.from_user
    chat_id = event.message.chat.id if is_callback else event.chat.id
    old_message = event.message if is_callback else None

    try:
        if is_callback:
            await old_message.edit_text(
                "⊡ sᴇɴᴅ ᴏʀ ᴜᴘʟᴏᴀᴅ ᴛʜᴇ ᴛʜᴜᴍʙɴᴀɪʟ ᴅɪʀᴇᴄᴛʟʏ ʜᴇʀᴇ!\n<code>ᴛɪᴍᴇᴏᴜᴛ 5 ᴍɪɴs</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            msg = await event.message.reply_text(
                "⊡ sᴇɴᴅ ᴏʀ ᴜᴘʟᴏᴀᴅ ᴛʜᴇ ᴛʜᴜᴍʙɴᴀɪʟ ᴅɪʀᴇᴄᴛʟʏ ʜᴇʀᴇ!\n<code>ᴛɪᴍᴇᴏᴜᴛ 5 ᴍɪɴs</code>",
                parse_mode=ParseMode.HTML
            )

        reply = await client.wait_for_message(
            chat_id=chat_id,
            from_user=user.id,
            filters=filters.photo,
            timeout=300
        )

        file_id = reply.photo.file_id
        await client.update_setting("thumb", file_id)

        if is_callback:
            await old_message.edit_text("⊡ ᴛʜᴜᴍʙɴᴀɪʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ")
        else:
            await msg.edit_text("⊡ ᴛʜᴜᴍʙɴᴀɪʟ ᴜᴘᴅᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ")

    except asyncio.TimeoutError:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛʀʏ ᴀɢᴀɪɴ •", callback_data="set_thumb")]
        ])
        if is_callback:
            await old_message.edit_text(
                "⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.",
                reply_markup=markup
            )
        else:
            await msg.edit_text(
                "⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ!\nᴄʟɪᴄᴋ ᴛʀʏ ᴀɢᴀɪɴ ᴛᴏ sᴇᴛ ᴛʜᴜᴍʙɴᴀɪʟ ᴀɢᴀɪɴ.",
                reply_markup=markup
            )



@Bot.on_message(filters.command("set_filename") & filters.user(OWNER_ID))
@Bot.on_callback_query(filters.regex("^set_filename$") & filters.user(OWNER_ID))
async def set_filename(client: Client, event):
    is_callback = isinstance(event, CallbackQuery)
    user = event.from_user
    chat_id = event.message.chat.id if is_callback else event.chat.id
    old_message = event.message if is_callback else None

    try:
        if is_callback:
            await old_message.edit_text(
                "⊡ sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ʜᴇʀᴇ!\n<code>ᴛɪᴍᴇᴏᴜᴛ 5 ᴍɪɴs</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            msg = await event.message.reply_text(
                "⊡ sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ʜᴇʀᴇ!\n<code>ᴛɪᴍᴇᴏᴜᴛ 5 ᴍɪɴs</code>",
                parse_mode=ParseMode.HTML
            )

        reply = await client.wait_for_message(
            chat_id=chat_id,
            from_user=user.id,
            filters=filters.text,
            timeout=300
        )

        fmt = reply.text.strip()
        await client.update_setting("filename", fmt)

        if is_callback:
            await old_message.edit_text(
                f"⊡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ᴜᴘᴅᴀᴛᴇᴅ\n<code>{fmt}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await msg.edit_text(
                f"⊡ ғɪʟᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ ᴜᴘᴅᴀᴛᴇᴅ\n<code>{fmt}</code>",
                parse_mode=ParseMode.HTML
            )

    except asyncio.TimeoutError:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛʀʏ ᴀɢᴀɪɴ •", callback_data="set_filename")]
        ])
        if is_callback:
            await old_message.edit_text(
                "⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ! ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.",
                reply_markup=markup
            )
        else:
            await msg.edit_text(
                "⊡ ʀᴇǫᴜᴇsᴛ ᴛɪᴍᴇᴏᴜᴛ!\nᴄʟɪᴄᴋ ᴛʀʏ ᴀɢᴀɪɴ ᴛᴏ sᴇᴛ ғɪʟᴇɴᴀᴍᴇ ᴀɢᴀɪɴ.",
                reply_markup=markup
            )
  