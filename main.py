import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message,
    CallbackQuery,
)

# -------------------- Configuration --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL = "@spark_news_tel"
CONTENT_CHANNEL = "@sanaooft"

CONTENT_MESSAGE_IDS = [
    165, 164, 163, 162, 161, 160, 159, 158, 157, 156,
    155, 154, 153, 152, 151, 150, 149, 148, 147, 146,
    145, 144, 143, 142, 141, 140, 139, 138, 137, 136,
    135, 134, 133, 132, 131, 130, 129, 128, 127, 126,
    125, 124, 123, 122, 121, 120, 119, 118, 117, 116,
    1,
]

# -------------------- Logging Setup --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Bot & Dispatcher --------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# کیبورد همیشگی با دکمه "ارسال محتوا"
content_request_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📥 ارسال محتوا")]],
    resize_keyboard=True,
    input_field_placeholder="برای دریافت محتوا کلیک کنید",
)

# -------------------- Helper Functions --------------------
async def is_user_member(user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال"""
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHANNEL, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        logger.warning(f"Failed to check membership for {user_id}: {e}")
        return False


async def send_random_content(chat_id: int) -> list[int]:
    """ارسال دو پیام رندوم از کانال محتوا و برگرداندن شناسه پیام‌های ارسالی"""
    try:
        selected_ids = random.sample(CONTENT_MESSAGE_IDS, 2)
    except ValueError:
        logger.error("Not enough message IDs to sample from.")
        return []

    sent_ids = []
    for msg_id in selected_ids:
        try:
            sent = await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=CONTENT_CHANNEL,
                message_id=msg_id,
            )
            sent_ids.append(sent.message_id)
        except Exception as e:
            logger.error(f"Failed to copy message ID {msg_id}: {e}")
    return sent_ids


async def delete_after_delay(chat_id: int, message_ids: list[int], delay: int = 15):
    """حذف پیام‌ها پس از مدتی مشخص"""
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.error(f"Failed to delete message {msg_id}: {e}")


# -------------------- Core logic (shared) --------------------
async def process_content_request(chat_id: int, user_id: int, reply_to_message: Message = None):
    """
    منطق اصلی درخواست محتوا (برای /start و دکمه "ارسال محتوا" یکسان)
    اگر کاربر عضو باشد، محتوا ارسال می‌شود، در غیر این صورت پیام عدم عضویت.
    """
    if await is_user_member(user_id):
        # ارسال تایید
        if reply_to_message:
            await reply_to_message.answer(
                "✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...",
                reply_markup=content_request_keyboard,
            )
        else:
            # اگر پیامی برای پاسخ نبود، برای chat_id ارسال کن (مثلاً از callback)
            await bot.send_message(
                chat_id=chat_id,
                text="✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...",
                reply_markup=content_request_keyboard,
            )

        # ارسال دو محتوای رندوم
        sent_ids = await send_random_content(chat_id)
        if sent_ids:
            note = await bot.send_message(
                chat_id=chat_id,
                text="⏳ این تصاویر بعد ۱۵ ثانیه پاک می‌شوند.",
            )
            asyncio.create_task(delete_after_delay(chat_id, sent_ids, 15))
            asyncio.create_task(delete_after_delay(chat_id, [note.message_id], 16))
    else:
        # کاربر عضو نیست
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 عضویت در کانال",
                        url="https://t.me/spark_news_tel",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ تایید عضویت",
                        callback_data="check_membership",
                    )
                ],
            ]
        )
        if reply_to_message:
            await reply_to_message.answer(
                "❌ برای استفاده از ربات ابتدا باید عضو کانال خبرگزاری شوید.",
                reply_markup=keyboard,
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ برای استفاده از ربات ابتدا باید عضو کانال خبرگزاری شوید.",
                reply_markup=keyboard,
            )


# -------------------- Handlers --------------------
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await process_content_request(message.chat.id, message.from_user.id, reply_to_message=message)


@dp.message(F.text == "📥 ارسال محتوا")
async def handle_content_button(message: Message) -> None:
    """مدیریت کلیک روی دکمه کیبورد"""
    await process_content_request(message.chat.id, message.from_user.id, reply_to_message=message)


@dp.callback_query(F.data == "check_membership")
async def check_membership_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id

    if await is_user_member(user_id):
        # ویرایش پیام قبلی و حذف دکمه‌های inline
        try:
            await callback.message.edit_text(
                "✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...",
                reply_markup=None,
            )
        except Exception:
            await callback.message.answer("✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...")

        # حالا مانند درخواست محتوای عادی عمل کن (از قبل تایید شده است)
        # نیازی به دوباره بررسی نیست، چون عضویت تازه تأیید شد
        sent_ids = await send_random_content(callback.message.chat.id)
        if sent_ids:
            note = await callback.message.answer("⏳ این تصاویر بعد ۱۵ ثانیه پاک می‌شوند.")
            asyncio.create_task(delete_after_delay(callback.message.chat.id, sent_ids, 15))
            asyncio.create_task(delete_after_delay(callback.message.chat.id, [note.message_id], 16))
        # نمایش کیبورد اصلی
        await callback.message.answer(
            "🔽 برای دریافت محتوای جدید، دکمه زیر را بزنید:",
            reply_markup=content_request_keyboard,
        )
    else:
        # هنوز عضو نیست → اعلان
        await callback.answer(
            text="❌ شما هنوز عضو کانال نشده‌اید.\nلطفاً ابتدا عضو شوید و سپس دکمه «تایید عضویت» را بزنید.",
            show_alert=True,
        )


# -------------------- Main --------------------
async def main() -> None:
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
