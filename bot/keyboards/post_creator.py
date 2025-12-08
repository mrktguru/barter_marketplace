from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_skip_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками 'Пропустить' и 'Отменить'"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_back_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками 'Назад' и 'Отменить'"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_payment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора доплаты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Нет", callback_data="payment_no")],
            [InlineKeyboardButton(text="Есть доплата", callback_data="payment_yes")],
            [InlineKeyboardButton(text="Обсуждается", callback_data="payment_discuss")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_marketplace_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора маркетплейса"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Wildberries", callback_data="marketplace_wb")],
            [InlineKeyboardButton(text="Ozon", callback_data="marketplace_ozon")],
            [InlineKeyboardButton(text="Другой маркетплейс", callback_data="marketplace_other")],
            [InlineKeyboardButton(text="Не применимо", callback_data="marketplace_na")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_expected_date_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора ожидаемой даты публикации"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Любая дата", callback_data="date_any")],
            [InlineKeyboardButton(text="Указать конкретную дату", callback_data="date_specific")],
            [InlineKeyboardButton(text="Указать период", callback_data="date_period")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_blog_theme_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора тематики блога"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Все тематики с женской ЦА", callback_data="theme_female")],
            [InlineKeyboardButton(text="Все тематики с мужской ЦА", callback_data="theme_male")],
            [InlineKeyboardButton(text="Детская тематика", callback_data="theme_child")],
            [InlineKeyboardButton(text="Любая тематика", callback_data="theme_any")],
            [InlineKeyboardButton(text="Указать свою", callback_data="theme_custom")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard


def get_social_networks_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора социальных сетей"""
    if selected is None:
        selected = []

    networks = [
        ("Instagram", "sn_instagram"),
        ("TikTok", "sn_tiktok"),
        ("Telegram", "sn_telegram"),
        ("VK", "sn_vk"),
        ("YouTube", "sn_youtube"),
    ]

    keyboard_buttons = []
    for name, callback in networks:
        checkmark = "✅ " if name in selected else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{checkmark}{name}", callback_data=callback)])

    keyboard_buttons.append([InlineKeyboardButton(text="Продолжить", callback_data="sn_continue")])
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def get_conditions_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора условий сотрудничества"""
    if selected is None:
        selected = []

    conditions = [
        ("Заказ товара по поисковому запросу", "cond_search"),
        ("Выкуп с ПВЗ", "cond_pickup"),
        ("Положительный отзыв 5⭐", "cond_review"),
        ("Съемка видео по ТЗ", "cond_video"),
        ("Не удалять контент", "cond_keep"),
    ]

    keyboard_buttons = []
    for name, callback in conditions:
        checkmark = "✅ " if name in selected else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{checkmark}{name}", callback_data=callback)])

    keyboard_buttons.append([InlineKeyboardButton(text="Добавить свои условия", callback_data="cond_custom")])
    keyboard_buttons.append([InlineKeyboardButton(text="Продолжить", callback_data="cond_continue")])
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def get_preview_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для предпросмотра поста"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕐 Опубликовать в очереди", callback_data="publish_queue")],
            [InlineKeyboardButton(text="⚡ Приоритетная публикация", callback_data="publish_priority")],
            [InlineKeyboardButton(text="💾 Сохранить в черновики", callback_data="save_draft")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_post")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")],
        ]
    )
    return keyboard
