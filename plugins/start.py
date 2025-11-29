from pyrogram import filters, Client
import psutil, shutil
from bot import Bot
from config import OWNER_ID, START_MSG, START_PHOTO
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

# tmp vars 
media_obj_store = {}

def main_media_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴇxᴘᴏʀᴛ sᴜʙ •", callback_data="extract_sub"),
            InlineKeyboardButton("• ɪᴍᴘᴏʀᴛ sᴜʙ •", callback_data="add_sub")
        ],
        [
            InlineKeyboardButton("• ʀᴇᴍᴏᴠᴇ sᴜʙ •", callback_data="remove_sub"),
            InlineKeyboardButton("• ᴛʜᴜᴍʙ •", callback_data="set_thumb")
        ],
        [
            InlineKeyboardButton("• ғɪʟᴇɴᴀᴍᴇ •", callback_data="set_filename"),
            InlineKeyboardButton("• ᴀᴜᴛᴏ ᴘʀᴏᴄᴇss •", callback_data="dummy")
        ],
        [
            InlineKeyboardButton("• ᴄʜᴀɴɢᴇ ᴠɪᴅ ғᴏʀᴍᴀᴛ •", callback_data="change_video_format")
        ],
        [
            InlineKeyboardButton(f"➕", callback_data="ep_add"),
            InlineKeyboardButton(f"➖", callback_data="ep_sub"),
            InlineKeyboardButton(f"📟", callback_data="ep_set")
        ]
    ])

@Bot.on_message(filters.command("start") & filters.user(OWNER_ID) & filters.private) 
async def start_message(client: Client, message: Message):
    user_id = message.from_user.id 
    bot_username = (await client.get_me()).username

    # usage
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    total, used, free = shutil.disk_usage("/")
    storage = used / total * 100

    # sys info 
    sys_info = f"<blockquote>sʏsᴛᴇᴍ ɪɴғᴏ\nᴄᴘᴜ - {cpu}%\nʀᴀᴍ - {ram}%\nsᴛᴏʀᴀɢᴇ- {storage:.1f}%</blockquote>"

    await client.send_photo(
        chat_id=user_id,
        photo=START_PHOTO,
        caption=f"{START_MSG}\n\n{sys_info}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Aᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{bot_username}?startgroup=botstart")
            ],
            [
                InlineKeyboardButton("• ᴏᴡɴᴇʀ •", url="https://t.me/OnlyNoco"),
                InlineKeyboardButton ("• ᴡᴇʙsɪᴛᴇ •", url="https://onlynoco.vercel.app")
            ]
        ]),
        parse_mode=ParseMode.HTML
    )

@Bot.on_message(
    filters.user(OWNER_ID) &
    (filters.video | (filters.document & filters.create(lambda _, __, m: m.document and (m.document.file_name.endswith((".mp4", ".mkv", ".webm"))))))
)
async def media_receiver(client: Client, message: Message): 
    media_obj_store[message.from_user.id] = message  # save file data

    await client.send_photo(
        chat_id=message.chat.id,
        caption=f"<blockquote>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!</blockquote>\n\n<blockquote>~ ᴛʜᴜᴍʙ - {client.thumb}\n~ ғɪʟᴇɴᴀᴍᴇ - {client.filename}\n~ ᴇᴘɪsᴏᴅᴇ - {client.episode}</blockquote>",
        photo=START_PHOTO,
        reply_markup = main_media_keyboard(),
        parse_mode=ParseMode.HTML
    )

# Episode callbacks
@Bot.on_callback_query(filters.regex("^(ep_add|ep_sub|ep_set|ep_cancel)$") & filters.user(OWNER_ID))
async def episode_control(client: Bot, query):
    await query.answer()
    action = query.data

    if action == "ep_add":
        client.episode += 1
        await client.update_settings("episode", client.episode)
    elif action == "ep_sub":
        client.episode = max(client.episode - 1, 0)
        await client.update_settings("episode", client.episode)
    elif action == "ep_set":
        client.pending_episode_msg = query.message_id
        await query.message.edit_caption(
            f"sᴇᴛ ᴀ ɴᴇᴡ ᴠᴀʟᴜᴇ ғᴏʀ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇ\nᴄᴜʀʀᴇɴᴛ: {client.episode}",
            reply_markup=ForceReply(True)
        )
        return
    elif action == "ep_cancel":
        if hasattr(client, "pending_episode_msg"):
            del client.pending_episode_msg

    # Update caption after add/sub/cancel
    await query.message.edit_caption(
        f"<blockquote>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!</blockquote>\n\n<blockquote>~ ᴛʜᴜᴍʙ - {client.thumb}\n~ ғɪʟᴇɴᴀᴍᴇ - {client.filename}\n~ ᴇᴘɪsᴏᴅᴇ - {client.episode}</blockquote>",
        reply_markup = main_media_keyboard()
    )

# ForceReply handler
@Bot.on_message(filters.user(OWNER_ID) & filters.reply)
async def force_reply_episode(client: Bot, message: Message):
    reply_msg = message.reply_to_message
    if not hasattr(client, "pending_episode_msg") or reply_msg.message_id != client.pending_episode_msg:
        return

    try:
        client.episode = int(message.text)
        await client.update_settings("episode", client.episode)
        del client.pending_episode_msg
        await reply_msg.edit_caption(
            f"<blockquote>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!</blockquote>\n\n<blockquote>~ ᴛʜᴜᴍʙ - {client.thumb}\n~ ғɪʟᴇɴᴀᴍᴇ - {client.filename}\n~ ᴇᴘɪsᴏᴅᴇ - {client.episode}</blockquote>",
            reply_markup = main_media_keyboard()
        )
        
        await message.reply(f"ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ {client.episode}")
    except ValueError:
        await message.reply("ᴠᴀʟᴜᴇ ᴇʀʀᴏʀ")

# Subtitle receiver
@Bot.on_message(
    filters.user(OWNER_ID) &
    (filters.document & filters.create(lambda _, __, m: m.document and (m.document.file_name.endswith((".srt", ".ass")))))
)
async def subtitle_receiver(client: Client, message: Message):
    media_obj_store[message.from_user.id] = message  # save file data

    await client.send_photo(
        chat_id=message.chat.id,
        photo=START_PHOTO,
        caption="sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴛʜɪs sᴜʙᴛɪᴛʟᴇ",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("• sʀᴛ •", callback_data="convert_sub_srt"),
                InlineKeyboardButton("• ᴀss •", callback_data="convert_sub_ass")
            ]
        ]),
        parse_mode=ParseMode.HTML
    )

@Bot.on_callback_query(filters.regex("^dummy$"))
async def dummy_handler(client, query):
    await query.answer()  # stops the spinner silently