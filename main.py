import asyncio
import json
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, ChatMemberUpdatedFilter
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message,
    CallbackQuery,
    ChatMemberUpdated,
)

# -------------------- Configuration --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8293164271

CHANNEL_ONE = "@spark_news_tel"
CHANNEL_TWO = "@spark_sport"
CHANNEL_THREE = "@spark_rap"

CONTENT_CHANNEL = "@sanaooft"
CONTENT_MESSAGE_IDS = [
    165, 164, 163, 162, 161, 160, 159, 158, 157, 156,
    155, 154, 153, 152, 151, 150, 149, 148, 147, 146,
    145, 144, 143, 142, 141, 140, 139, 138, 137, 136,
    135, 134, 133, 132, 131, 130, 129, 128, 127, 126,
    125, 124, 123, 122, 121, 120, 119, 118, 117, 116,
    1,
]

STAGE_FILE = "user_stages.json"

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Bot & Dispatcher --------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# کیبورد همیشگی
content_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📥 ارسال محتوا")]],
    resize_keyboard=True,
    input_field_placeholder="برای دریافت محتوا کلیک کنید",
)

# -------------------- File‑based stage storage --------------------
def load_stages() -> dict[int, int]:
    try:
        with open(STAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_stages(stages: dict[int, int]) -> None:
    with open(STAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(stages, f, ensure_ascii=False, indent=2)

user_stage = load_stages()

# -------------------- Helper Functions --------------------
async def is_member(user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        logger.warning(f"عضویت {user_id} در {channel} بررسی نشد: {e}")
        return False

async def missing_channels(user_id: int, channels: list[str]) -> list[str]:
    missing = []
    for ch in channels:
        if not await is_member(user_id, ch):
            missing.append(ch)
    return missing

def required_channels(stage: int) -> list[str]:
    if stage == 0:
        return [CHANNEL_ONE]
    elif stage == 1:
        return [CHANNEL_ONE, CHANNEL_TWO]
    else:
        return [CHANNEL_ONE, CHANNEL_TWO, CHANNEL_THREE]

def missing_keyboard(missing: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in missing:
        link = f"https://t.me/{ch.lstrip('@')}"
        buttons.append([InlineKeyboardButton(text=f"📢 عضویت در {ch}", url=link)])
    buttons.append([InlineKeyboardButton(text="✅ تایید عضویت", callback_data="check_membership")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_random_content(chat_id: int) -> list[int]:
    try:
        selected = random.sample(CONTENT_MESSAGE_IDS, 2)
    except ValueError:
        return []
    sent = []
    for mid in selected:
        try:
            msg = await bot.copy_message(chat_id, CONTENT_CHANNEL, mid)
            sent.append(msg.message_id)
        except Exception as e:
            logger.error(f"کپی پیام {mid} ناموفق: {e}")
    return sent

async def delete_later(chat_id: int, ids: list[int], delay: int = 15):
    await asyncio.sleep(delay)
    for mid in ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception as e:
            logger.error(f"حذف پیام {mid} ناموفق: {e}")

# -------------------- Core --------------------
async def handle_content_request(chat_id: int, user_id: int, reply: Message | None):
    stage = user_stage.get(user_id, 0)
    req = required_channels(stage)
    miss = await missing_channels(user_id, req)

    if miss:
        text = "❌ برای استفاده از ربات، باید عضو کانال‌های زیر باشید:\n\n"
        text += "\n".join(f"• {ch}" for ch in miss)
        kb = missing_keyboard(miss)
        if reply:
            await reply.answer(text, reply_markup=kb)
        else:
            await bot.send_message(chat_id, text, reply_markup=kb)
        return

    user_stage[user_id] = stage + 1
    save_stages(user_stage)

    if reply:
        await reply.answer("✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...", reply_markup=content_keyboard)
    else:
        await bot.send_message(chat_id, "✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...", reply_markup=content_keyboard)

    sent = await send_random_content(chat_id)
    if sent:
        note = await bot.send_message(chat_id, "⏳ این تصاویر بعد ۱۵ ثانیه پاک می‌شوند.")
        asyncio.create_task(delete_later(chat_id, sent, 15))
        asyncio.create_task(delete_later(chat_id, [note.message_id], 16))

# -------------------- Notification Handler (FIXED) --------------------
@dp.chat_member(
    ChatMemberUpdatedFilter(
        # تابع فیلتر: وقتی کاربر از left/kicked به member/admin تبدیل شود
        lambda update: update.new_chat_member.status in ["member", "administrator"]
        and update.old_chat_member.status in ["left", "kicked"]
    )
)
async def on_user_join(event: ChatMemberUpdated):
    """وقتی کاربری عضو یکی از کانال‌ها می‌شود، به ادمین اطلاع بده."""
    user = event.new_chat_member.user
    chat = event.chat
    user_info = f"👤 {user.full_name}" + (f" (@{user.username})" if user.username else "")
    text = (
        f"✅ کاربر جدید عضو کانال شد!\n\n"
        f"{user_info}\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"📢 کانال: {chat.title} (`{chat.username or chat.id}`)"
    )
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"ارسال نوتیفیکیشن به ادمین ناموفق: {e}")

# -------------------- User Handlers --------------------
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await handle_content_request(message.chat.id, message.from_user.id, message)

@dp.message(F.text == "📥 ارسال محتوا")
async def btn_handler(message: Message):
    await handle_content_request(message.chat.id, message.from_user.id, message)

@dp.callback_query(F.data == "check_membership")
async def verify_cb(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    stage = user_stage.get(user_id, 0)
    req = required_channels(stage)
    miss = await missing_channels(user_id, req)

    if miss:
        text = "❌ برای استفاده از ربات، باید عضو کانال‌های زیر باشید:\n\n"
        text += "\n".join(f"• {ch}" for ch in miss)
        kb = missing_keyboard(miss)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
    else:
        await handle_content_request(callback.message.chat.id, user_id, None)

# -------------------- Main --------------------
async def main():
    logger.info("ربات با ذخیره‌سازی مرحله و نوتیفیکیشن اجرا شد...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
