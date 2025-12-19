# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar 
#
# All rights reserved.
#
# This code is the intellectual property of @WTF_Phantom.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: king25258069@gmail.com

import html
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Bot
from telegram.constants import ParseMode, ChatType
from telegram.error import TelegramError
from baka.database import users_collection, sudoers_collection, groups_collection
from baka.config import OWNER_ID, SUDO_IDS_STR, LOGGER_ID, BOT_NAME, AUTO_REVIVE_HOURS, AUTO_REVIVE_BONUS

SUDO_USERS = set()

def reload_sudoers():
    """Loads Sudo users from Env and DB."""
    SUDO_USERS.clear()
    SUDO_USERS.add(OWNER_ID)
    if SUDO_IDS_STR:
        for x in SUDO_IDS_STR.split(","):
            if x.strip().isdigit(): SUDO_USERS.add(int(x.strip()))
    for doc in sudoers_collection.find({}):
        SUDO_USERS.add(doc["user_id"])

reload_sudoers()

# --- 🌟 ULTIMATE LOGGER ---
async def log_to_channel(bot: Bot, event_type: str, details: dict):
    if LOGGER_ID == 0: return
    now = datetime.now().strftime("%I:%M %p | %d %b")
    
    headers = {
        "start": "🟢 <b>𝐁𝐎𝐓 𝐃𝐄𝐏𝐋𝐎𝐘𝐄𝐃</b>",
        "join": "🆕 <b>𝐍𝐄𝐖 𝐆𝐑𝐎𝐔𝐏</b>",
        "leave": "❌ <b>𝐋𝐄𝐅𝐓 𝐆𝐑𝐎𝐔𝐏</b>",
        "command": "⚠️ <b>𝐀𝐃𝐌𝐈𝐍 𝐋𝐎𝐆</b>",
        "transfer": "💸 <b>𝐓𝐑𝐀𝐍𝐒𝐀𝐂𝐓𝐈𝐎𝐍</b>"
    }
    header = headers.get(event_type, "🔔 <b>𝐋𝐎𝐆</b>")

    text = f"{header}\n\n📅 <b>Time:</b> <code>{now}</code>\n"
    if 'user' in details: text += f"👤 <b>Trigger:</b> {details['user']}\n"
    if 'chat' in details: text += f"📍 <b>Chat:</b> {html.escape(details['chat'])}\n"
    if 'action' in details: text += f"🎬 <b>Action:</b> {details['action']}\n"
    if 'link' in details and details['link'] != "No Link": text += f"🔗 <b>Link:</b> <a href='{details['link']}'>Click Here</a>\n"
    text += f"\n🤖 <i>{BOT_NAME} Systems</i>"

    try: await bot.send_message(chat_id=LOGGER_ID, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except: pass

# --- HELPERS ---

def get_mention(user_data, custom_name=None):
    if hasattr(user_data, "id"): 
        name = custom_name or user_data.first_name
        return f"<a href='tg://user?id={user_data.id}'><b>{html.escape(name)}</b></a>"
    elif isinstance(user_data, dict):
        name = custom_name or user_data.get("name", "User")
        uid = user_data.get("user_id")
        return f"<a href='tg://user?id={uid}'><b>{html.escape(name)}</b></a>"
    return "Unknown"

def check_auto_revive(user_doc):
    if user_doc['status'] != 'dead': return False
    death_time = user_doc.get('death_time')
    if not death_time: return False
    if datetime.utcnow() - death_time > timedelta(hours=AUTO_REVIVE_HOURS):
        users_collection.update_one(
            {"user_id": user_doc["user_id"]}, 
            {
                "$set": {"status": "alive", "death_time": None},
                "$inc": {"balance": AUTO_REVIVE_BONUS}
            }
        )
        return True
    return False

def ensure_user_exists(tg_user):
    user_doc = users_collection.find_one({"user_id": tg_user.id})
    username = tg_user.username.lower() if tg_user.username else None
    
    if not user_doc:
        new_user = {
            "user_id": tg_user.id, 
            "name": tg_user.first_name, 
            "username": username, 
            "is_bot": tg_user.is_bot,
            "balance": 0,            # Main Currency
            "inventory": [],         # RPG Items
            "waifus": [],            # Collected Characters
            "daily_streak": 0,       # Reward Streak
            "last_daily": None,
            "kills": 0, 
            "status": "alive", 
            "protection_expiry": datetime.utcnow(), 
            "registered_at": datetime.utcnow(), 
            "death_time": None, 
            "seen_groups": []
        }
        users_collection.insert_one(new_user)
        return new_user
    else:
        if check_auto_revive(user_doc): 
            user_doc['status'] = 'alive'
            user_doc['balance'] += AUTO_REVIVE_BONUS
        
        updates = {}
        if user_doc.get("username") != username: updates["username"] = username
        if user_doc.get("name") != tg_user.first_name: updates["name"] = tg_user.first_name
        if "waifu_coins" in user_doc: users_collection.update_one({"user_id": tg_user.id}, {"$unset": {"waifu_coins": ""}})
        
        if updates: users_collection.update_one({"user_id": tg_user.id}, {"$set": updates})
        return user_doc

def track_group(chat, user):
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if not groups_collection.find_one({"chat_id": chat.id}):
            groups_collection.insert_one({"chat_id": chat.id, "title": chat.title, "claimed": False})
        if user:
            users_collection.update_one(
                {"user_id": user.id}, 
                {"$addToSet": {"seen_groups": chat.id}}
            )

async def resolve_target(update, context, specific_arg=None):
    if update.message.reply_to_message:
        return ensure_user_exists(update.message.reply_to_message.from_user), None

    query = specific_arg if specific_arg else (context.args[0] if context.args else None)
    if query:
        if query.isdigit():
            doc = users_collection.find_one({"user_id": int(query)})
            if doc: return doc, None
            return None, f"❌ <b>Baka!</b> ID <code>{query}</code> not found."
        if query.startswith("@"):
            clean = query.strip("@").lower()
            doc = users_collection.find_one({"username": clean})
            if doc: return doc, None
            return None, f"❌ <b>Oops!</b> <code>@{clean}</code> not found."
    return None, "No target"

def is_protected(user_data):
    if user_data.get("protection_expiry") and user_data["protection_expiry"] > datetime.utcnow(): return True
    partner_id = user_data.get("partner_id")
    if partner_id:
        partner = users_collection.find_one({"user_id": partner_id})
        if partner and partner.get("protection_expiry") and partner["protection_expiry"] > datetime.utcnow(): return True
    return False

def get_active_protection(user_data):
    now = datetime.utcnow()
    self_expiry = user_data.get("protection_expiry")
    partner_expiry = None
    partner_id = user_data.get("partner_id")
    if partner_id:
        partner = users_collection.find_one({"user_id": partner_id})
        if partner: partner_expiry = partner.get("protection_expiry")
    valid_expiries = []
    if self_expiry and self_expiry > now: valid_expiries.append(self_expiry)
    if partner_expiry and partner_expiry > now: valid_expiries.append(partner_expiry)
    if not valid_expiries: return None
    return max(valid_expiries)

def format_money(amount): return f"${amount:,}"

def format_time(timedelta_obj):
    total_seconds = int(timedelta_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- SMART FONT STYLER ---
def stylize_text(text):
    """
    Converts normal text to Aesthetic Math Sans Bold.
    SKIPS: @mentions, links, and code blocks.
    """
    font_map = {
        'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴩ', 'q': 'q', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
    }
    
    def apply_style(t):
        return "".join(font_map.get(c, c) for c in t)

    # Split by Mentions, Links, Commands, Code
    # This Regex keeps them separate so we don't stylize them
    pattern = r"(@\w+|https?://\S+|`[^`]+`|/[a-zA-Z0-9_]+)"
    parts = re.split(pattern, text)
    
    result = []
    for part in parts:
        if re.match(pattern, part):
            result.append(part) # Keep original (Command/Mention/Link)
        else:
            result.append(apply_style(part)) # Apply Style to Normal Text
            
    return "".join(result)
