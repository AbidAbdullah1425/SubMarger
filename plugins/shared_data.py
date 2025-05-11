import logging
import asyncio
from typing import Dict, Any
from datetime import datetime
from pyrogram.types import Message

# Configure logging
logger = logging.getLogger(__name__)

# Shared data dictionaries
global_mode = AUTO_MODE
user_data: Dict[int, Dict[str, Any]] = {}
user_tasks: Dict[int, asyncio.Task] = {}

# Mode constants
AUTO_MODE = "auto"
MANUAL_MODE = "manual"

def get_user_data(user_id: int) -> Dict[str, Any]:
    """Get or create user data for a user"""
    if user_id not in user_data:
        user_data[user_id] = {
            "mode": AUTO_MODE,
            "video": None,
            "subtitle": None,
            "new_name": None,
            "caption": None,
            "channel_msg": None,
            "status_message": None,
            "last_update": datetime.now(),
            "task_started": datetime.now()
        }
    return user_data[user_id]

def update_message_reference(user_id: int, message_type: str, message: Message) -> None:
    """Update message reference in user data"""
    try:
        data = get_user_data(user_id)
        data[message_type] = message
        data["last_update"] = datetime.now()
    except Exception as e:
        logger.error(f"Error updating {message_type} for user {user_id}: {str(e)}")

def get_message_reference(user_id: int, message_type: str) -> Message:
    """Get message reference from user data"""
    try:
        return user_data.get(user_id, {}).get(message_type)
    except Exception as e:
        logger.error(f"Error getting {message_type} for user {user_id}: {str(e)}")
        return None

def clean_user_data(user_id: int) -> None:
    """Clean up user data and cancel any running tasks"""
    try:
        logger.info(f"Cleaning up data for user {user_id}")
        
        # Cancel task if exists
        if user_id in user_tasks:
            task = user_tasks[user_id]
            if not task.done():
                task.cancel()
            del user_tasks[user_id]

        # Clean up user data
        if user_id in user_data:
            del user_data[user_id]

    except Exception as e:
        logger.error(f"Error cleaning up data for user {user_id}: {str(e)}")

def register_task(user_id: int, task: asyncio.Task) -> None:
    """Register a new task for a user"""
    try:
        # Cancel existing task if any
        if user_id in user_tasks:
            clean_user_data(user_id)
        user_tasks[user_id] = task
    except Exception as e:
        logger.error(f"Error registering task for user {user_id}: {str(e)}")

def get_current_mode(user_id: int = None) -> str:
    """Get the current mode for a user or global mode"""
    if user_id is not None:
        return get_user_data(user_id).get("mode", AUTO_MODE)
    return user_data.get("global_mode", AUTO_MODE)

def is_auto_mode(user_id: int = None) -> bool:
    """Check if in auto mode"""
    return get_current_mode(user_id) == AUTO_MODE

def switch_mode(user_id: int = None) -> str:
    """Switch between auto and manual modes"""
    if user_id is not None:
        user_data = get_user_data(user_id)
        current_mode = user_data.get("mode", AUTO_MODE)
        new_mode = MANUAL_MODE if current_mode == AUTO_MODE else AUTO_MODE
        user_data["mode"] = new_mode
        logger.info(f"Mode switched to {new_mode} for user {user_id}")
    else:
        current_mode = get_current_mode()
        new_mode = MANUAL_MODE if current_mode == AUTO_MODE else AUTO_MODE
        user_data["global_mode"] = new_mode
        logger.info(f"Global mode switched to {new_mode}")
    return new_mode

def is_task_running(user_id: int) -> bool:
    """Check if a task is running for the user"""
    return user_id in user_tasks and not user_tasks[user_id].done()

async def cleanup_old_data():
    """Periodically clean up old data"""
    while True:
        try:
            current_time = datetime.now()
            for user_id in list(user_data.keys()):
                data = user_data[user_id]
                # Clean up data older than 1 hour
                if (current_time - data["task_started"]).total_seconds() > 3600:
                    clean_user_data(user_id)
        except Exception as e:
            logger.error(f"Error in cleanup_old_data: {str(e)}")
        await asyncio.sleep(300)  # Run every 5 minutes

# Initialize cleanup task
def init_cleanup():
    """Initialize the cleanup task"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(cleanup_old_data())
    except Exception as e:
        logger.error(f"Error initializing cleanup task: {str(e)}")