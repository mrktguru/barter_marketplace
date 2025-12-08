from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню для рекламодателя"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать пост")],
            [KeyboardButton(text="💾 Мои черновики"), KeyboardButton(text="📋 Мои публикации")],
            [KeyboardButton(text="ℹ️ Информация")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню для администратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Панель администратора")],
            [KeyboardButton(text="📝 Создать пост")],
            [KeyboardButton(text="💾 Мои черновики"), KeyboardButton(text="📋 Мои публикации")],
            [KeyboardButton(text="ℹ️ Информация")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Панель администратора"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Настройки канала", callback_data="admin_channel")],
            [InlineKeyboardButton(text="⏰ Расписание публикаций", callback_data="admin_schedule")],
            [InlineKeyboardButton(text="💰 Тарифы и цены", callback_data="admin_prices")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📋 Очередь публикаций", callback_data="admin_queue")],
            [InlineKeyboardButton(text="⚡ Приоритетные публикации", callback_data="admin_priority")],
        ]
    )
    return keyboard
