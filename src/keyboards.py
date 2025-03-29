from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData

admin_menu = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="➕ Add company"), KeyboardButton(text="🏢 All companies")],
        [KeyboardButton(text="✏️ Edit company"), KeyboardButton(text="❌ Delete company")],
        [KeyboardButton(text="➕ Add user"), KeyboardButton(text="👥 All users")],
        [KeyboardButton(text="✏️ Edit user"), KeyboardButton(text="❌ Remove user")]
    ]
)

user_menu = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="⏳ Add auto notification"), KeyboardButton(text="🔎 Provide currently status")],
        [KeyboardButton(text="➕ Add status notification"), KeyboardButton(text="⚠️ Add warning notification")],
        [KeyboardButton(text="🗺 Set To Location"), KeyboardButton(text="🕔 Distance left/ETA")],
        [KeyboardButton(text="🎊 My notifications"), KeyboardButton(text="❌ Delete notification")],
        [KeyboardButton(text="🧹 Clear all notifications")]
    ]
)

cancel_button = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="⬅️ Cancel")]
    ]
)
cancel_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Cancel", callback_data="cancel")]
])