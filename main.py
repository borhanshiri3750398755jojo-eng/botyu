import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

# -------------------- Configuration --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Railway environment variable
TARGET_CHANNEL = "@spark_news_tel"  # Channel for membership check
CONTENT_CHANNEL = "@sanaooft"       # Channel from which content is copied

# Message IDs to randomly select for content forwarding
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

# -------------------- Helper Functions --------------------
async def is_user_member(user_id: int) -> bool:
    """Check if user is a member of the target channel."""
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHANNEL, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        logger.warning(f"Failed to check membership for {user_id}: {e}")
        return False


async def send_random_content(chat_id: int) -> list[int]:
    """
    Copy two random messages from CONTENT_CHANNEL to the user.
    Returns a list of the message_id of the sent copies.
    Errors are logged but don't crash the bot.
    """
    try:
        selected_ids = random.sample(CONTENT_MESSAGE_IDS, 2)
    except ValueError:
        logger.error("Not enough message IDs to sample from.")
        return []

    sent_message_ids = []
    for msg_id in selected_ids:
        try:
            sent = await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=CONTENT_CHANNEL,
                message_id=msg_id,
            )
            sent_message_ids.append(sent.message_id)
        except Exception as e:
            logger.error(f"Failed to copy message ID {msg_id}: {e}")
    return sent_message_ids


async def delete_after_delay(chat_id: int, message_ids: list[int], delay: int = 15):
    """Wait `delay` seconds, then delete the messages with given IDs."""
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.error(f"Failed to delete message {msg_id}: {e}")


# -------------------- Handlers --------------------
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command."""
    user_id = message.from_user.id

    if await is_user_member(user_id):
        await message.answer("✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...")
        sent_ids = await send_random_content(message.chat.id)
        if sent_ids:
            # Send notification and schedule deletion
            note = await message.answer("⏳ این تصاویر بعد ۱۵ ثانیه پاک می‌شوند.")
            asyncio.create_task(delete_after_delay(message.chat.id, sent_ids, 15))
            # Optionally delete the notification after the content is gone
            asyncio.create_task(delete_after_delay(message.chat.id, [note.message_id], 16))
    else:
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
        await message.answer(
            "❌ برای استفاده از ربات ابتدا باید عضو کانال خبرگزاری شوید.",
            reply_markup=keyboard,
        )


@dp.callback_query(F.data == "check_membership")
async def check_membership_callback(callback: CallbackQuery) -> None:
    """Handle the 'تایید عضویت' button press."""
    await callback.answer()
    user_id = callback.from_user.id

    if await is_user_member(user_id):
        # Membership confirmed
        try:
            await callback.message.edit_text(
                "✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...",
                reply_markup=None,
            )
        except Exception:
            await callback.message.answer("✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...")

        sent_ids = await send_random_content(callback.message.chat.id)
        if sent_ids:
            note = await callback.message.answer("⏳ این تصاویر بعد ۱۵ ثانیه پاک می‌شوند.")
            asyncio.create_task(delete_after_delay(callback.message.chat.id, sent_ids, 15))
            asyncio.create_task(delete_after_delay(callback.message.chat.id, [note.message_id], 16))
    else:
        # Still not a member → show alert only
        await callback.answer(
            text="❌ شما هنوز عضو کانال نشده‌اید.\nلطفاً ابتدا عضو شوید و سپس دکمه «تایید عضویت» را بزنید.",
            show_alert=True,
        )


# -------------------- Main Entry Point --------------------
async def main() -> None:
    """Start the bot using long polling."""
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
