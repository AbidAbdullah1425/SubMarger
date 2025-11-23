from pyrogram import Client, filters 
import psutil, shutil
from bot import Bot
from database.database import update_settings
from config import OWNER_ID, START_MSG, START_PHOTO
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

# tmp vars 
media_obj_store = {}





@Bot.on_message(filters.command("start") & filters.user(OWNER_ID) & filters.private) 
async def start_message(client: Client, message: Message):
  user_id = message.from_user.id 
  bot_username = (await client.get_me()).username
  
  #usuage
  cpu = psutil.cpu_percent()  # fixed typo
  ram = psutil.virtual_memory().percent  # fixed typo
  total, used, free = shutil.disk_usage("/")  # fixed typo
  storage = used / total * 100
  
  #sys info 
  sys_info = f"sʏsᴛᴇᴍ ɪɴғᴏ\nᴄᴘᴜ - {cpu}%\nʀᴀᴍ - {ram}%\nsᴛᴏʀᴀɢᴇ- {storage:.1f}%"
  
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
    )]
  )
  
  
@Bot.on_message(
    filters.user(OWNER_ID) &  # fixed OWNER_IDS -> OWNER_ID
    (filters.video | (filters.document & filters.create(lambda _, __, m: m.document and (m.document.file_name.endswith((".mp4", ".mkv", ".webm"))))))
)
async def media_receiver(client: Client, message: Message): 
    media_obj_store[message.from_user.id] = message # save file data for later callback usuage
  
    await client.send_photo(  # fixed client.message.send_photo -> client.send_photo
        chat_id=message.chat.id,  # added missing chat_id
        caption=f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!\n\n~ ᴛʜᴜᴍʙ - {getattr(client, 'thumb', '')}\n ~ ғɪʟᴇɴᴀᴍᴇ - {getattr(client, 'filename', '')}\n ~ ᴇᴘɪsᴏᴅᴇ - {getattr(client, 'episode', 1)}", 
        photo=START_PHOTO,
        reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴇxᴘᴏʀᴛ sᴜʙ •", callback_data="extract_sub"),
            InlineKeyboardButton("• ɪᴍᴘᴏʀᴛ sᴜʙ •", callback_data="add_sub")  # fixed missing callback_data
        ],
        [
            InlineKeyboardButton("• ʀᴇᴍᴏᴠᴇ sᴜʙ •", callback_data="remove_sub"),
            InlineKeyboardButton("• ᴛʜᴜᴍʙ •", callback_data="set_thumb")  # swapped fix (was set_filename)
        ],
        [
            InlineKeyboardButton("• ғɪʟᴇɴᴀᴍᴇ •", callback_data="set_filename"),  # swapped fix (was set_thumb)
            InlineKeyboardButton("• ᴀᴜᴛᴏ ᴘʀᴏᴄᴇss •", callback_data="dummy")
        ],
        [
            InlineKeyboardButton("• ᴄʜᴀɴɢᴇ ᴠɪᴅ ғᴏʀᴍᴀᴛ •", callback_data="change_video_format")  # fixed callback -> callback_data
        ],
        [
            InlineKeyboardButton(f"➕", callback_data="ep_add"),
            InlineKeyboardButton(f"➖", callback_data="ep_sub"),
            InlineKeyboardButton(f"📟", callback_data="ep_set")
        ]
    ]),
    parse_mode=ParseMode.HTML
  )





# Callback for episode control
@Bot.on_callback_query(filters.regex("^(ep_add|ep_sub|ep_set|ep_cancel)$") & filters.user(OWNER_ID))  # fixed OWNER_IDS -> OWNER_ID
async def episode_control(client: Bot, query):
    await query.answer()
    action = query.data

    if action == "ep_add":
        client.episode += 1
        await client.update_setting("episode", client.episode)
        await query.message.edit_caption(
            f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!\n\n"
            f"~ ᴛʜᴜᴍʙ - {getattr(client, 'thumb', '')}\n"
            f"~ ғɪʟᴇɴᴀᴍᴇ - {getattr(client, 'filename', '')}\n"
            f"~ ᴇᴘɪsᴏᴅᴇ - {getattr(client, 'episode', 1)}"
        )

    elif action == "ep_sub":
        client.episode = max(client.episode - 1, 0)
        await client.update_setting("episode", client.episode)
        await query.message.edit_caption(
            f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!\n\n"
            f"~ ᴛʜᴜᴍʙ - {getattr(client, 'thumb', '')}\n"
            f"~ ғɪʟᴇɴᴀᴍᴇ - {getattr(client, 'filename', '')}\n"
            f"~ ᴇᴘɪsᴏᴅᴇ - {getattr(client, 'episode', 1)}"
        )

    elif action == "ep_set":
        client.pending_episode_msg = query.message.message_id
        await query.message.edit_caption(
            f"sᴇᴛ ᴀ ɴᴇᴡ ᴠᴀʟᴜᴇ ғᴏʀ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇ\n"
            f"ᴄᴜʀʀᴇɴᴛ: {getattr(client, 'episode', 1)}",
            reply_markup=ForceReply(True)  # <-- Force reply always
        )

    elif action == "ep_cancel":
        if hasattr(client, "pending_episode_msg"):
            del client.pending_episode_msg
        await query.message.edit_caption(
            f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!\n\n"
            f"~ ᴛʜᴜᴍʙ - {getattr(client, 'thumb', '')}\n"
            f"~ ғɪʟᴇɴᴀᴍᴇ - {getattr(client, 'filename', '')}\n"
            f"~ ᴇᴘɪsᴏᴅᴇ - {getattr(client, 'episode', 1)}"
        )

# ForceReply handler
@Bot.on_message(filters.user(OWNER_ID) & filters.reply)
async def force_reply_episode(client: Bot, message: Message):
    reply_msg = message.reply_to_message
    if not hasattr(client, "pending_episode_msg") or reply_msg.message_id != client.pending_episode_msg:
        return  # ignore unrelated replies

    try:
        client.episode = int(message.text)
        await client.update_setting("episode", client.episode)
        del client.pending_episode_msg
        await reply_msg.edit_caption(
            f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴡɪᴛʜ ᴛʜɪs ᴍᴇᴅɪᴀ ғɪʟᴇ ᴀɴᴅ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴀᴛ ʙᴀsᴇᴅ ᴏɴ ʏᴏᴜʀ ᴅᴇsɪʀᴇ!\n\n"
            f"~ ᴛʜᴜᴍʙ - {getattr(client, 'thumb', '')}\n"
            f"~ ғɪʟᴇɴᴀᴍᴇ - {getattr(client, 'filename', '')}\n"
            f"~ ᴇᴘɪsᴏᴅᴇ - {getattr(client, 'episode', 1)}"
        )
        await message.reply(f"ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ {client.episode}")
    except ValueError:
        await message.reply("ᴠᴀʟᴜᴇ ᴇʀʀᴏʀ")





@Bot.on_message(
    filters.user(OWNER_ID) &
    (filters.document & filters.create(lambda _, __, m: m.document and (m.document.file_name.endswith((".srt", ".ass")))))
)
async def subtitle_receiver(client: Client, message: Message):
  media_obj_store[message.from_user.id] = message # save file data for later callback usuage 
  
  await client.send_photo(
    chat_id=message.chat.id,  # added missing chat_id
    caption=f"sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴏ ᴛʜɪs ᴛʜɪs sᴜʙᴛɪᴛʟᴇ",
    photo=START_PHOTO,
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