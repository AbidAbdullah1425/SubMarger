from pyrogram import filters
from bot import Bot
from config import OWNER_IDS
from .shared_data import switch_mode, logger

@Bot.on_message(filters.user(OWNER_IDS) & filters.command("mode"))
async def handle_mode_switch(client, message):
    """Switch between auto and manual processing modes (owner only)"""
    try:
        new_mode = switch_mode(message.from_user.id)
        
        await message.reply(
            f"✅ Mode switched to: {new_mode.upper()}\n"
            f"{'🤖 Automatic subtitle processing enabled' if new_mode == 'auto' else '👤 Manual subtitle processing enabled'}"
        )
        
    except Exception as e:
        logger.error(f"Error in switch_mode: {e}")
        await message.reply("❌ Error switching modes. Please try again.")