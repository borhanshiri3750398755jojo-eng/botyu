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
    """
    Check if the user is a member of the target channel.
    Returns True if the user is a member (any status except 'left' or 'kicked'),
    False otherwise or if an error occurs.
    """
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHANNEL, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        logger.warning(f"Failed to check membership for {user_id}: {e}")
        return False


async def send_random_content(chat_id: int) -> None:
    """
    Select two random, distinct message IDs from CONTENT_MESSAGE_IDS
    and forward (copy) them from the content channel to the user.
    If a forward fails, the error is logged and the process continues.
    """
    try:
        selected_ids = random.sample(CONTENT_MESSAGE_IDS, 2)
    except ValueError:
        # In case the list contains fewer than 2 items (should not happen here)
        logger.error("Not enough message IDs to sample from.")
        return

    for msg_id in selected_ids:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=CONTENT_CHANNEL,
                message_id=msg_id,
            )
        except Exception as e:
            logger.error(f"Failed to copy message ID {msg_id}: {e}")


# -------------------- Handlers --------------------
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command."""
    user_id = message.from_user.id

    if await is_user_member(user_id):
        # User is already a member → confirm and send content
        await message.answer("✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...")
        await send_random_content(message.chat.id)
    else:
        # User is not a member → show join prompt with inline buttons
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
    await callback.answer()  # Acknowledge the callback to remove loading state
    user_id = callback.from_user.id

    if await is_user_member(user_id):
        # Membership confirmed → edit the prompt message and send content
        await callback.message.edit_text(
            "✅ عضویت شما تایید شد.\n\nدر حال ارسال محتوا...",
            reply_markup=None,  # Remove the inline buttons
        )
        await send_random_content(callback.message.chat.id)
    else:
        # Still not a member → show the same prompt again (edit text/buttons)
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
        await callback.message.edit_text(
            "❌ برای استفاده از ربات ابتدا باید عضو کانال خبرگزاری شوید.",
            reply_markup=keyboard,
        )


# -------------------- Main Entry Point --------------------
async def main() -> None:
    """Start the bot using long polling."""
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
