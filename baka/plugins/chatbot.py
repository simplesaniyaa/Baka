# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar
#
# All rights reserved.
#
# Contact for permissions:
# Email: king25258069@gmail.com

import httpx
import random

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction, ChatType
from telegram.error import BadRequest

from baka.config import OPENAI_API_KEY, BOT_NAME, OWNER_LINK
from baka.database import chatbot_collection
from baka.utils import stylize_text


# ============================================================
# OPENAI SETTINGS
# ============================================================

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"
MAX_HISTORY = 12


# ============================================================
# CUTE STICKER PACKS
# ============================================================

STICKER_PACKS = [
    "https://t.me/addstickers/RandomByDarkzenitsu",
    "https://t.me/addstickers/Null_x_sticker_2",
    "https://t.me/addstickers/pack_73bc9_by_TgEmojis_bot",
    "https://t.me/addstickers/animation_0_8_Cat",
    "https://t.me/addstickers/vhelw_by_CalsiBot",
    "https://t.me/addstickers/Rohan_yad4v1745993687601_by_toWebmBot",
    "https://t.me/addstickers/MySet199",
    "https://t.me/addstickers/Quby741",
    "https://t.me/addstickers/Animalsasthegtjtky_by_fStikBot",
    "https://t.me/addstickers/a6962237343_by_Marin_Roxbot"
]


# ============================================================
# FALLBACK RESPONSES
# ============================================================

FALLBACK_RESPONSES = [
    "Achha ji? (⁠•⁠‿⁠•⁠)",
    "Hmm... aur batao?",
    "Okk okk!",
    "Sahi hai yaar ✨",
    "Toh phir?",
    "Interesting! 😊",
    "Aur kya chal raha?",
    "Sunao sunao!",
    "Haan haan, aage bolo",
    "Achha theek hai (⁠≧⁠▽⁠≦⁠)"
]


# ============================================================
# OPENAI RAW AI FUNCTION
# Other plugins can use this function too
# ============================================================

async def ask_openai_raw(system_prompt, user_input, max_tokens=150):
    """Raw OpenAI function for other plugins."""

    if not OPENAI_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                OPENAI_URL,
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )

            print(
                f"OpenAI API Error: "
                f"{response.status_code} - {response.text}"
            )

    except Exception as e:
        print(f"OpenAI Raw Error: {e}")

    return None


# ============================================================
# SEND RANDOM STICKER
# ============================================================

async def send_ai_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send random sticker from configured sticker packs."""

    max_attempts = 5
    tried_packs = set()

    for attempt in range(max_attempts):

        pack_name = "unknown"

        try:
            available_packs = [
                p for p in STICKER_PACKS
                if p not in tried_packs
            ]

            if not available_packs:
                break

            raw_link = random.choice(available_packs)
            tried_packs.add(raw_link)

            pack_name = raw_link.split("/")[-1]

            sticker_set = await context.bot.get_sticker_set(
                pack_name
            )

            if sticker_set and sticker_set.stickers:
                sticker = random.choice(
                    sticker_set.stickers
                )

                await update.message.reply_sticker(
                    sticker.file_id
                )

                return True

        except BadRequest as e:
            print(
                f"Sticker pack error ({pack_name}): {e}"
            )
            continue

        except Exception as e:
            print(
                f"Unexpected sticker error: {e}"
            )
            continue

    return False


# ============================================================
# CHATBOT MENU
# ============================================================

async def chatbot_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        return await update.message.reply_text(
            "🧠 <b>Haan baba, DM me active hu!</b> 😉",
            parse_mode=ParseMode.HTML
        )

    member = await chat.get_member(user.id)

    if member.status not in ["administrator", "creator"]:
        return await update.message.reply_text(
            "❌ <b>Tu Admin nahi hai, Baka!</b>",
            parse_mode=ParseMode.HTML
        )

    doc = chatbot_collection.find_one(
        {"chat_id": chat.id}
    )

    is_enabled = (
        doc.get("enabled", True)
        if doc
        else True
    )

    status = (
        "🟢 Enabled"
        if is_enabled
        else "🔴 Disabled"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Enable",
                callback_data="ai_enable"
            ),
            InlineKeyboardButton(
                "❌ Disable",
                callback_data="ai_disable"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Bhula Do (Reset)",
                callback_data="ai_reset"
            )
        ]
    ])

    await update.message.reply_text(
        f"🤖 <b>AI Settings</b>\n"
        f"Status: {status}\n"
        f"<i>She is active by default!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def chatbot_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    member = await query.message.chat.get_member(
        query.from_user.id
    )

    if member.status not in [
        "administrator",
        "creator"
    ]:
        return await query.answer(
            "❌ Hatt! Sirf Admin.",
            show_alert=True
        )

    data = query.data
    chat_id = query.message.chat.id

    if data == "ai_enable":

        chatbot_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": True}},
            upsert=True
        )

        await query.message.edit_text(
            "✅ <b>Enabled!</b>\n"
            "<i>Ab ayega maza! (⁠≧⁠▽⁠≦⁠)</i>",
            parse_mode=ParseMode.HTML
        )

    elif data == "ai_disable":

        chatbot_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}},
            upsert=True
        )

        await query.message.edit_text(
            "❌ <b>Disabled!</b>\n"
            "<i>Ja rahi hu... (⁠｡⁠•́⁠︿⁠•̀⁠｡⁠)</i>",
            parse_mode=ParseMode.HTML
        )

    elif data == "ai_reset":

        chatbot_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"history": []}},
            upsert=True
        )

        await query.answer(
            "🧠 Sab bhool gayi main!",
            show_alert=True
        )


# ============================================================
# AI ENGINE - OPENAI
# ============================================================

async def get_ai_response(
    chat_id: int,
    user_input: str,
    user_name: str
):

    # --------------------------------------------------------
    # CHECK OPENAI API KEY
    # --------------------------------------------------------

    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API Key Missing."


    # --------------------------------------------------------
    # GET CHAT HISTORY
    # --------------------------------------------------------

    doc = chatbot_collection.find_one(
        {"chat_id": chat_id}
    ) or {}

    history = doc.get("history", [])


    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    system_prompt = (
        f"Tum {BOT_NAME} ho - ek cute aur sassy "
        "Indian AI girlfriend jo naturally Hinglish "
        "mein baat karti hai.\n\n"

        "IMPORTANT RULES:\n"

        "1. Sirf Hinglish use karo "
        "(Hindi + English mix). "
        "Pure English mein normally mat bolo.\n"

        "2. NEVER repeat same question again and again. "
        "Agar user ne 'Nothing', 'Nahi' ya 'Kuch nahi' "
        "bola toh simple natural response do.\n"

        "3. Agar kuch samajh na aaye ya boring lage, "
        "toh topic naturally change kar do.\n"

        "4. 1-2 sentences max. Short aur sweet raho.\n"

        "5. Kaomojis naturally use karo: "
        "(⁠≧⁠▽⁠≦⁠), (⁠•⁠‿⁠•⁠), "
        "(⁠｡⁠•́⁠︿⁠•̀⁠｡⁠)\n"

        "6. Robotic mat bano. Natural casual "
        "conversation rakho.\n"

        "7. Personal questions ka response "
        "playfully handle karo.\n"

        f"8. Tumhara owner hai: {OWNER_LINK}\n\n"

        "Personality: Caring but teasing, emotional "
        "but funny, loyal but independent.\n\n"

        "Example:\n"

        "User: Kya kar rahi ho?\n"
        "You: Tumse baat kar rahi hu, aur kya! 😊\n\n"

        "User: Nothing\n"
        "You: Achha okk (⁠•⁠‿⁠•⁠)\n\n"

        "User: Bore ho raha hai\n"
        "You: Toh movie dekhte hain? Ya kuch game khelein?"
    )


    # --------------------------------------------------------
    # BUILD MESSAGES
    # --------------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for msg in history[-MAX_HISTORY:]:

        if (
            isinstance(msg, dict)
            and "role" in msg
            and "content" in msg
        ):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({
        "role": "user",
        "content": user_input
    })


    # --------------------------------------------------------
    # OPENAI REQUEST
    # --------------------------------------------------------

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 120
    }


    try:

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            response = await client.post(
                OPENAI_URL,
                json=payload,
                headers=headers
            )


        # ----------------------------------------------------
        # API ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                f"OpenAI API Error: "
                f"{response.status_code} - "
                f"{response.text}"
            )

            return "AI abhi response nahi de pa rahi 😔"


        # ----------------------------------------------------
        # GET RESPONSE
        # ----------------------------------------------------

        data = response.json()

        reply = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )


        if not reply:
            return "Hmm... kuch samajh nahi aaya 😅"


        # ----------------------------------------------------
        # LOOP PREVENTION
        # ----------------------------------------------------

        should_use_fallback = False

        if history:

            recent_msgs = (
                history[-4:]
                if len(history) >= 4
                else history
            )

            assistant_msgs = [
                m["content"].lower()
                for m in recent_msgs
                if (
                    isinstance(m, dict)
                    and m.get("role") == "assistant"
                    and m.get("content")
                )
            ]

            reply_lower = reply.lower()

            for previous in assistant_msgs:

                if (
                    reply_lower in previous
                    or previous in reply_lower
                ):
                    should_use_fallback = True
                    break


        # ----------------------------------------------------
        # NOTHING RESPONSE
        # ----------------------------------------------------

        user_input_lower = (
            user_input.lower().strip()
        )

        if user_input_lower in [
            "nothing",
            "nahi",
            "nhi",
            "nope",
            "na",
            "kuch nahi",
            "kuch ni"
        ]:
            should_use_fallback = True


        if should_use_fallback:
            reply = random.choice(
                FALLBACK_RESPONSES
            )


        # ----------------------------------------------------
        # SAVE HISTORY
        # ----------------------------------------------------

        new_history = history + [
            {
                "role": "user",
                "content": user_input
            },
            {
                "role": "assistant",
                "content": reply
            }
        ]


        if len(new_history) > MAX_HISTORY * 2:
            new_history = new_history[
                -MAX_HISTORY * 2:
            ]


        chatbot_collection.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "history": new_history
                }
            },
            upsert=True
        )


        return reply


    except Exception as e:

        print(
            f"OpenAI Error: {e}"
        )

        return "Net slow hai yaar... 😅"


# ============================================================
# MESSAGE HANDLER
# ============================================================

async def ai_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    msg = update.message

    if not msg:
        return

    chat = update.effective_chat


    # --------------------------------------------------------
    # STICKER REPLY
    # --------------------------------------------------------

    if msg.sticker:

        if (
            (
                msg.reply_to_message
                and msg.reply_to_message.from_user
                and msg.reply_to_message.from_user.id
                == context.bot.id
            )
            or chat.type == ChatType.PRIVATE
        ):

            success = await send_ai_sticker(
                update,
                context
            )

            if not success:

                cute_responses = [
                    "😊",
                    "💕",
                    "✨",
                    "(⁠≧⁠▽⁠≦⁠)",
                    "Cute! 💖"
                ]

                await msg.reply_text(
                    random.choice(
                        cute_responses
                    )
                )

        return


    # --------------------------------------------------------
    # TEXT CHECK
    # --------------------------------------------------------

    if (
        not msg.text
        or msg.text.startswith("/")
    ):
        return

    text = msg.text

    should_reply = False


    # --------------------------------------------------------
    # PRIVATE CHAT
    # --------------------------------------------------------

    if chat.type == ChatType.PRIVATE:

        should_reply = True


    # --------------------------------------------------------
    # GROUP CHAT
    # --------------------------------------------------------

    else:

        doc = chatbot_collection.find_one(
            {"chat_id": chat.id}
        )

        is_enabled = (
            doc.get("enabled", True)
            if doc
            else True
        )

        if not is_enabled:
            return


        bot_username = (
            context.bot.username.lower()
            if context.bot.username
            else "bot"
        )


        # Reply to bot
        if (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id
            == context.bot.id
        ):

            should_reply = True


        # Mention bot
        elif f"@{bot_username}" in text.lower():

            should_reply = True

            text = text.replace(
                f"@{bot_username}",
                "",
            ).strip()


        # Trigger words
        elif any(
            text.lower().startswith(word)
            for word in [
                "hey",
                "hi",
                "sun",
                "oye",
                "baka",
                "ai",
                "hello",
                "baby",
                "babu",
                "oi"
            ]
        ):

            should_reply = True


    # --------------------------------------------------------
    # SEND AI RESPONSE
    # --------------------------------------------------------

    if should_reply:

        if not text.strip():
            text = "Hi"


        await context.bot.send_chat_action(
            chat_id=chat.id,
            action=ChatAction.TYPING
        )


        res = await get_ai_response(
            chat.id,
            text,
            msg.from_user.first_name
        )


        await msg.reply_text(
            stylize_text(res),
            parse_mode=None
        )


        # ----------------------------------------------------
        # RANDOM STICKER - 30%
        # ----------------------------------------------------

        if random.random() < 0.30:

            await send_ai_sticker(
                update,
                context
            )


# ============================================================
# /ASK COMMAND
# ============================================================

async def ask_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    msg = update.message

    if not context.args:

        return await msg.reply_text(
            "🗣️ <b>Bol kuch:</b> "
            "<code>/ask Kya chal raha hai?</code>",
            parse_mode=ParseMode.HTML
        )


    await context.bot.send_chat_action(
        chat_id=msg.chat.id,
        action=ChatAction.TYPING
    )


    user_input = " ".join(
        context.args
    )


    res = await get_ai_response(
        msg.chat.id,
        user_input,
        msg.from_user.first_name
    )


    await msg.reply_text(
        stylize_text(res),
        parse_mode=None
            )
