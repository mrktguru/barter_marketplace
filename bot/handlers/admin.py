from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from bot.config import config
from bot.database import get_db
from bot.database.crud import (
    get_user_by_telegram_id,
    get_posts_in_queue,
    get_scheduled_posts,
    get_setting_value,
    update_setting,
    get_setting
)
from bot.keyboards.main_menu import get_admin_panel_keyboard, get_admin_menu_keyboard
from bot.states.post_states import AdminStates

router = Router()


# ===== ГЛАВНОЕ МЕНЮ АДМИНА =====

@router.message(F.text == "⚙️ Панель администратора")
async def admin_panel_handler(message: Message):
    """Главное меню панели администратора"""
    telegram_id = message.from_user.id

    # Проверка прав администратора
    if not config.is_admin(telegram_id):
        await message.answer("⛔ У вас нет прав доступа к панели администратора.")
        return

    db = next(get_db())
    try:
        # Проверка настройки канала
        channel_id = get_setting_value(db, 'channel_id')

        # Получение статистики
        queue_posts = get_posts_in_queue(db)
        priority_posts = get_scheduled_posts(db)

        queue_count = len(queue_posts)
        priority_count = len(priority_posts)

        # Получение количества рекламодателей
        from bot.database.models import User
        advertisers_count = db.query(User).filter(User.role == 'advertiser').count()

        if not channel_id:
            text = (
                "⚙️ <b>Панель администратора</b>\n\n"
                f"Добро пожаловать, {message.from_user.first_name}!\n\n"
                "⚠️ <b>ВНИМАНИЕ! Канал не настроен</b>\n"
                "Бот не сможет публиковать посты без настройки канала.\n"
            )
        else:
            text = (
                "⚙️ <b>Панель администратора</b>\n\n"
                f"Добро пожаловать, {message.from_user.first_name}!\n\n"
                "Выберите раздел:\n"
            )

        await message.answer(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

    finally:
        db.close()


# ===== НАСТРОЙКИ КАНАЛА =====

@router.callback_query(F.data == "admin_channel")
async def admin_channel_handler(callback: CallbackQuery, state: FSMContext):
    """Настройки канала"""
    db = next(get_db())
    try:
        channel_id = get_setting_value(db, 'channel_id')
        channel_username = get_setting_value(db, 'channel_username')

        if not channel_id:
            text = (
                "⚠️ <b>Канал не настроен</b>\n\n"
                "Для работы бота необходимо настроить канал для публикаций.\n\n"
                "<b>Что нужно сделать:</b>\n\n"
                "1️⃣ Создайте канал в Telegram\n"
                "   (если еще не создан)\n\n"
                "2️⃣ Добавьте бота в администраторы канала\n"
                f"   Бот: @{callback.bot.username}\n\n"
                "3️⃣ Выдайте боту права:\n"
                "   ✓ Публикация сообщений\n"
                "   ✓ Редактирование сообщений\n\n"
                "4️⃣ Добавьте канал в настройках бота\n\n"
                "❗️ Без настройки канала публикации работать не будут!"
            )
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_channel")],
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])
        else:
            text = (
                "📢 <b>Настройки канала</b>\n\n"
                "<b>Текущий статус:</b>\n\n"
                f"Канал: {channel_username or channel_id}\n"
                f"ID: {channel_id}\n\n"
                "Статус подключения: ✅ Активен\n"
                "Права бота: ✅ Может публиковать\n"
            )
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить канал", callback_data="admin_change_channel")],
                [InlineKeyboardButton(text="🔄 Проверить подключение", callback_data="admin_check_channel")],
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_handler(callback: CallbackQuery, state: FSMContext):
    """Начало добавления канала"""
    text = (
        "➕ <b>Добавление канала</b>\n\n"
        "Отправьте одно из следующего:\n\n"
        "• Username канала (начинается с @)\n"
        "  Пример: @barter_bloggers\n\n"
        "• ID канала (отрицательное число)\n"
        "  Пример: -1001234567890\n\n"
        "• Ссылку на канал\n"
        "  Пример: https://t.me/barter_bloggers\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "Убедитесь, что бот уже добавлен в администраторы канала с правами на публикацию!"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_channel")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.set_channel)


@router.message(AdminStates.set_channel)
async def admin_set_channel_handler(message: Message, state: FSMContext):
    """Обработка ввода канала"""
    channel_input = message.text.strip()

    # Парсинг ввода
    if channel_input.startswith('@'):
        channel_id = channel_input
    elif channel_input.startswith('https://t.me/'):
        channel_id = '@' + channel_input.split('/')[-1]
    elif channel_input.lstrip('-').isdigit():
        channel_id = int(channel_input)
    else:
        await message.answer("❌ Неверный формат. Пожалуйста, отправьте username, ID или ссылку на канал.")
        return

    # Проверка канала
    try:
        chat = await message.bot.get_chat(channel_id)

        # Проверка прав бота
        bot_member = await message.bot.get_chat_member(channel_id, message.bot.id)

        if bot_member.status not in ['administrator', 'creator']:
            await message.answer(
                "❌ <b>Ошибка подключения</b>\n\n"
                "Бот не является администратором канала.\n\n"
                "<b>Что нужно сделать:</b>\n"
                f"1. Откройте канал {channel_id}\n"
                "2. Настройки канала → Администраторы\n"
                f"3. Добавьте бота @{message.bot.username}\n"
                "4. Выдайте права:\n"
                "   ✓ Публикация сообщений\n"
                "   ✓ Редактирование сообщений\n"
                "5. Попробуйте снова",
                parse_mode="HTML"
            )
            return

        # Сохранение в БД
        db = next(get_db())
        try:
            update_setting(db, 'channel_id', str(chat.id))
            update_setting(db, 'channel_username', chat.username or str(chat.id))

            await message.answer(
                "✅ <b>Канал успешно настроен!</b>\n\n"
                f"Название: {chat.title}\n"
                f"Username: @{chat.username or 'не установлен'}\n"
                f"ID: {chat.id}\n\n"
                "Бот готов к публикации постов!",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )

            await state.clear()

        finally:
            db.close()

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка при проверке канала</b>\n\n"
            f"Детали: {str(e)}\n\n"
            "Убедитесь, что:\n"
            "• Канал существует\n"
            "• Бот добавлен в администраторы\n"
            "• У бота есть права на публикацию",
            parse_mode="HTML"
        )


# ===== РАСПИСАНИЕ ПУБЛИКАЦИЙ =====

@router.callback_query(F.data == "admin_schedule")
async def admin_schedule_handler(callback: CallbackQuery):
    """Настройки расписания"""
    db = next(get_db())
    try:
        posts_per_day = get_setting_value(db, 'posts_per_day', '5')
        schedule_times = get_setting_value(db, 'schedule_times', '10:00,13:00,16:00,19:00,22:00')

        times_list = [t.strip() for t in schedule_times.split(',')]
        times_display = '\n'.join([f"🕐 {time}" for time in times_list])

        text = (
            "⏰ <b>Расписание публикаций</b>\n\n"
            "<b>Текущие настройки:</b>\n\n"
            f"Постов в день: {posts_per_day}\n"
            f"График публикаций:\n{times_display}\n\n"
            "Статус: ✅ Автопубликация включена"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить количество постов", callback_data="admin_change_posts_count")],
            [InlineKeyboardButton(text="⏰ Изменить время публикаций", callback_data="admin_change_schedule")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== ТАРИФЫ И ЦЕНЫ =====

@router.callback_query(F.data == "admin_prices")
async def admin_prices_handler(callback: CallbackQuery):
    """Управление тарифами"""
    db = next(get_db())
    try:
        queue_price = get_setting_value(db, 'queue_price', '0')
        priority_price = get_setting_value(db, 'priority_price', '500')

        text = (
            "💰 <b>Тарифы и цены</b>\n\n"
            "<b>Текущие тарифы:</b>\n\n"
            "📊 Публикация в очереди\n"
            f"Цена: {queue_price}₽ {'(БЕСПЛАТНО)' if queue_price == '0' else ''}\n\n"
            "⚡ Приоритетная публикация\n"
            f"Цена: {priority_price}₽\n"
            "Статус: Активен"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить цену очереди", callback_data="admin_change_queue_price")],
            [InlineKeyboardButton(text="✏️ Изменить цену приоритета", callback_data="admin_change_priority_price")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== ОЧЕРЕДЬ ПУБЛИКАЦИЙ =====

@router.callback_query(F.data == "admin_queue")
async def admin_queue_handler(callback: CallbackQuery):
    """Просмотр очереди"""
    db = next(get_db())
    try:
        queue_posts = get_posts_in_queue(db)

        if not queue_posts:
            text = (
                "📋 <b>Очередь публикаций</b>\n\n"
                "Очередь пуста\n\n"
                "В данный момент нет постов, ожидающих публикации.\n\n"
                "Рекламодатели могут добавлять посты через бота."
            )
        else:
            posts_text = ""
            for idx, post in enumerate(queue_posts[:5], 1):
                user = post.user
                posts_text += (
                    f"\n{idx}️⃣ {post.product_name[:30]}...\n"
                    f"   От: @{user.username or user.full_name}\n"
                    f"   Позиция: №{post.queue_position}\n"
                )

            remaining = len(queue_posts) - 5
            if remaining > 0:
                posts_text += f"\n... и еще {remaining} постов"

            text = (
                "📋 <b>Очередь публикаций</b>\n\n"
                f"Всего в очереди: {len(queue_posts)} постов\n"
                f"Ближайшие публикации:{posts_text}"
            )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== ПРИОРИТЕТНЫЕ ПУБЛИКАЦИИ =====

@router.callback_query(F.data == "admin_priority")
async def admin_priority_handler(callback: CallbackQuery):
    """Просмотр приоритетных"""
    db = next(get_db())
    try:
        priority_posts = get_scheduled_posts(db)

        if not priority_posts:
            text = (
                "⚡ <b>Приоритетные публикации</b>\n\n"
                "Нет запланированных приоритетных публикаций\n\n"
                "Рекламодатели могут заказать приоритетную публикацию за 500₽"
            )
        else:
            posts_text = ""
            for idx, post in enumerate(priority_posts[:5], 1):
                user = post.user
                posts_text += (
                    f"\n⚡ {post.scheduled_time.strftime('%d.%m в %H:%M')}\n"
                    f"   {post.product_name[:30]}...\n"
                    f"   От: @{user.username or user.full_name}\n"
                )

            remaining = len(priority_posts) - 5
            if remaining > 0:
                posts_text += f"\n... и еще {remaining} постов"

            text = (
                "⚡ <b>Приоритетные публикации</b>\n\n"
                f"Запланировано: {len(priority_posts)} постов\n"
                f"Календарь:{posts_text}"
            )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== СТАТИСТИКА =====

@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Общая статистика"""
    db = next(get_db())
    try:
        from bot.database.models import User, Post

        advertisers_count = db.query(User).filter(User.role == 'advertiser').count()
        published_posts = db.query(Post).filter(Post.status == 'published').count()
        queue_posts = len(get_posts_in_queue(db))
        priority_posts = len(get_scheduled_posts(db))

        text = (
            "📊 <b>Статистика бота</b>\n\n"
            "<b>За все время:</b>\n"
            f"👥 Рекламодателей: {advertisers_count}\n"
            f"📝 Опубликовано постов: {published_posts}\n\n"
            "<b>Текущее состояние:</b>\n"
            f"📋 В очереди: {queue_posts} постов\n"
            f"⚡ Запланировано: {priority_posts} постов\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ =====

@router.callback_query(F.data == "admin_back")
async def admin_back_handler(callback: CallbackQuery):
    """Возврат в главное меню админа"""
    telegram_id = callback.from_user.id

    if not config.is_admin(telegram_id):
        await callback.answer("⛔ У вас нет прав доступа.")
        return

    db = next(get_db())
    try:
        channel_id = get_setting_value(db, 'channel_id')

        if not channel_id:
            text = (
                "⚙️ <b>Панель администратора</b>\n\n"
                f"Добро пожаловать, {callback.from_user.first_name}!\n\n"
                "⚠️ <b>ВНИМАНИЕ! Канал не настроен</b>\n"
                "Бот не сможет публиковать посты без настройки канала.\n"
            )
        else:
            text = (
                "⚙️ <b>Панель администратора</b>\n\n"
                f"Добро пожаловать, {callback.from_user.first_name}!\n\n"
                "Выберите раздел:\n"
            )

        await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")

    finally:
        db.close()
