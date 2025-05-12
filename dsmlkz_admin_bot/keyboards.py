from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_action_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📄 Parse as News", callback_data="parse_news"),
        InlineKeyboardButton("💼 Parse as Job", callback_data="parse_job"),
        InlineKeyboardButton("✏️ Generate Job", callback_data="generate_job"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
    )
    return keyboard


def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Yes", callback_data="confirm_save"),
        InlineKeyboardButton("❌ No", callback_data="cancel_save"),
    )
    return keyboard
