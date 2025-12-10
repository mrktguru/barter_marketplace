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
    # Получение информации о боте
    bot_info = await callback.bot.get_me()

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
                f"   Бот: @{bot_info.username}\n\n"
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

    # Получение информации о боте
    bot_info = await message.bot.get_me()

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
                f"3. Добавьте бота @{bot_info.username}\n"
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


@router.callback_query(F.data == "admin_change_channel")
async def admin_change_channel_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение канала"""
    text = (
        "✏️ <b>Изменение канала</b>\n\n"
        "Отправьте новый канал одним из способов:\n\n"
        "• Username канала (начинается с @)\n"
        "  Пример: @barter_bloggers\n\n"
        "• ID канала (отрицательное число)\n"
        "  Пример: -1001234567890\n\n"
        "• Ссылку на канал\n"
        "  Пример: https://t.me/barter_bloggers\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "Убедитесь, что бот уже добавлен в администраторы нового канала с правами на публикацию!"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_channel")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.set_channel)


@router.callback_query(F.data == "admin_check_channel")
async def admin_check_channel_handler(callback: CallbackQuery):
    """Проверка подключения канала"""
    db = next(get_db())
    try:
        channel_id = get_setting_value(db, 'channel_id')

        if not channel_id:
            await callback.answer("❌ Канал не настроен", show_alert=True)
            return

        # Попытка получить информацию о канале
        try:
            # Преобразуем в int если это число
            if channel_id.lstrip('-').isdigit():
                channel_id = int(channel_id)

            chat = await callback.bot.get_chat(channel_id)
            bot_member = await callback.bot.get_chat_member(channel_id, callback.bot.id)

            # Проверка прав
            can_post = bot_member.status in ['administrator', 'creator']

            # Получение дополнительной информации
            member_count = await callback.bot.get_chat_member_count(channel_id)

            if can_post:
                text = (
                    "✅ <b>Канал подключен успешно!</b>\n\n"
                    "<b>Информация о канале:</b>\n"
                    f"Название: {chat.title}\n"
                    f"Username: @{chat.username or 'не установлен'}\n"
                    f"ID: {chat.id}\n"
                    f"Подписчиков: {member_count}\n\n"
                    "<b>Статус бота:</b>\n"
                    f"Роль: {bot_member.status}\n"
                    "Права: ✅ Может публиковать\n\n"
                    "Все проверки пройдены! Бот готов к работе."
                )
            else:
                text = (
                    "⚠️ <b>Проблема с правами!</b>\n\n"
                    "<b>Информация о канале:</b>\n"
                    f"Название: {chat.title}\n"
                    f"Username: @{chat.username or 'не установлен'}\n"
                    f"ID: {chat.id}\n\n"
                    "<b>Статус бота:</b>\n"
                    f"Роль: {bot_member.status}\n"
                    "Права: ❌ Недостаточно прав\n\n"
                    "Бот должен быть администратором канала с правами на публикацию сообщений!"
                )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_channel")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            text = (
                "❌ <b>Ошибка подключения!</b>\n\n"
                f"Не удалось подключиться к каналу.\n\n"
                f"<b>Детали ошибки:</b>\n{str(e)}\n\n"
                "<b>Возможные причины:</b>\n"
                "• Бот удален из канала\n"
                "• Канал удален или заблокирован\n"
                "• Неверный ID канала\n\n"
                "Рекомендуется изменить канал в настройках."
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить канал", callback_data="admin_change_channel")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_channel")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


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


@router.callback_query(F.data == "admin_change_posts_count")
async def admin_change_posts_count_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение количества постов в день"""
    db = next(get_db())
    try:
        posts_per_day = get_setting_value(db, 'posts_per_day', '5')

        text = (
            "✏️ <b>Изменение количества постов</b>\n\n"
            f"Текущее количество: {posts_per_day} постов в день\n\n"
            "Введите новое количество постов, которое должно публиковаться в день:\n\n"
            "Рекомендуется: 3-10 постов в день\n"
            "Минимум: 1 пост\n"
            "Максимум: 50 постов"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_schedule")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AdminStates.set_posts_count)

    finally:
        db.close()


@router.message(AdminStates.set_posts_count)
async def admin_set_posts_count_handler(message: Message, state: FSMContext):
    """Обработка нового количества постов"""
    try:
        count = int(message.text.strip())

        if count < 1:
            await message.answer("❌ Количество постов должно быть не менее 1. Попробуйте снова:")
            return

        if count > 50:
            await message.answer("❌ Количество постов не должно превышать 50. Попробуйте снова:")
            return

        # Сохранение в БД
        db = next(get_db())
        try:
            update_setting(db, 'posts_per_day', str(count))

            await message.answer(
                f"✅ <b>Количество постов изменено!</b>\n\n"
                f"Новое значение: {count} постов в день\n\n"
                "Изменения вступят в силу при следующей публикации.",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )

            await state.clear()

        finally:
            db.close()

    except ValueError:
        await message.answer("❌ Неверный формат. Введите целое число (например: 5):")


@router.callback_query(F.data == "admin_change_schedule")
async def admin_change_schedule_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение времени публикаций"""
    db = next(get_db())
    try:
        schedule_times = get_setting_value(db, 'schedule_times', '10:00,13:00,16:00,19:00,22:00')

        times_list = [t.strip() for t in schedule_times.split(',')]
        times_display = '\n'.join([f"🕐 {time}" for time in times_list])

        text = (
            "⏰ <b>Изменение времени публикаций</b>\n\n"
            f"Текущее расписание:\n{times_display}\n\n"
            "Введите новое расписание в формате времени через запятую:\n\n"
            "<b>Пример:</b>\n"
            "10:00, 14:00, 18:00, 22:00\n\n"
            "<b>Требования:</b>\n"
            "• Формат времени: ЧЧ:ММ (24-часовой)\n"
            "• Разделитель: запятая\n"
            "• Минимум 1 время\n"
            "• Время должно быть уникальным"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_schedule")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AdminStates.set_schedule_times)

    finally:
        db.close()


@router.message(AdminStates.set_schedule_times)
async def admin_set_schedule_times_handler(message: Message, state: FSMContext):
    """Обработка нового расписания"""
    schedule_input = message.text.strip()

    # Парсинг времени
    times_list = [t.strip() for t in schedule_input.split(',')]

    # Валидация
    import re
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')

    valid_times = []
    for time_str in times_list:
        if not time_pattern.match(time_str):
            await message.answer(
                f"❌ Неверный формат времени: {time_str}\n\n"
                "Используйте формат ЧЧ:ММ (например: 09:00, 14:30)\n"
                "Попробуйте снова:"
            )
            return

        valid_times.append(time_str)

    if not valid_times:
        await message.answer("❌ Необходимо указать хотя бы одно время. Попробуйте снова:")
        return

    # Проверка на уникальность
    if len(valid_times) != len(set(valid_times)):
        await message.answer("❌ Время должно быть уникальным. Попробуйте снова:")
        return

    # Сортировка времени
    valid_times.sort()

    # Сохранение в БД
    db = next(get_db())
    try:
        schedule_str = ', '.join(valid_times)
        update_setting(db, 'schedule_times', schedule_str)

        times_display = '\n'.join([f"🕐 {time}" for time in valid_times])

        await message.answer(
            f"✅ <b>Расписание обновлено!</b>\n\n"
            f"Новое расписание:\n{times_display}\n\n"
            f"Публикаций в день: {len(valid_times)}\n\n"
            "Изменения вступят в силу при следующей публикации.",
            parse_mode="HTML",
            reply_markup=get_admin_menu_keyboard()
        )

        await state.clear()

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


@router.callback_query(F.data == "admin_change_queue_price")
async def admin_change_queue_price_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение цены очереди"""
    db = next(get_db())
    try:
        queue_price = get_setting_value(db, 'queue_price', '0')

        text = (
            "✏️ <b>Изменение цены очереди</b>\n\n"
            f"Текущая цена: {queue_price}₽\n\n"
            "Введите новую цену для публикации в очереди:\n\n"
            "• Введите 0 для бесплатной публикации\n"
            "• Или укажите цену в рублях (целое число)\n\n"
            "Примеры: 0, 100, 250, 500"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_prices")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AdminStates.set_queue_price)

    finally:
        db.close()


@router.message(AdminStates.set_queue_price)
async def admin_set_queue_price_handler(message: Message, state: FSMContext):
    """Обработка новой цены очереди"""
    try:
        price = int(message.text.strip())

        if price < 0:
            await message.answer("❌ Цена не может быть отрицательной. Попробуйте снова:")
            return

        # Сохранение в БД
        db = next(get_db())
        try:
            old_price = get_setting_value(db, 'queue_price', '0')
            update_setting(db, 'queue_price', str(price))

            # Логирование изменения
            from bot.database.models import AdminLog
            log_entry = AdminLog(
                admin_id=message.from_user.id,
                action='change_queue_price',
                details=f"Изменена цена очереди: {old_price}₽ → {price}₽"
            )
            db.add(log_entry)
            db.commit()

            status_text = "БЕСПЛАТНО" if price == 0 else f"{price}₽"

            await message.answer(
                f"✅ <b>Цена очереди изменена!</b>\n\n"
                f"Старая цена: {old_price}₽\n"
                f"Новая цена: {status_text}\n\n"
                "Новая цена будет применяться для всех новых постов.",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )

            await state.clear()

        finally:
            db.close()

    except ValueError:
        await message.answer("❌ Неверный формат. Введите целое число (например: 0, 100, 500):")


@router.callback_query(F.data == "admin_change_priority_price")
async def admin_change_priority_price_handler(callback: CallbackQuery, state: FSMContext):
    """Изменение цены приоритета"""
    db = next(get_db())
    try:
        priority_price = get_setting_value(db, 'priority_price', '500')

        text = (
            "✏️ <b>Изменение цены приоритета</b>\n\n"
            f"Текущая цена: {priority_price}₽\n\n"
            "Введите новую цену для приоритетной публикации:\n\n"
            "• Укажите цену в рублях (целое число)\n"
            "• Рекомендуется: 300-1000₽\n\n"
            "Примеры: 300, 500, 1000"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_prices")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AdminStates.set_priority_price)

    finally:
        db.close()


@router.message(AdminStates.set_priority_price)
async def admin_set_priority_price_handler(message: Message, state: FSMContext):
    """Обработка новой цены приоритета"""
    try:
        price = int(message.text.strip())

        if price < 0:
            await message.answer("❌ Цена не может быть отрицательной. Попробуйте снова:")
            return

        if price == 0:
            await message.answer(
                "⚠️ Вы действительно хотите сделать приоритетную публикацию бесплатной?\n"
                "Это может привести к переполнению приоритетной очереди.\n\n"
                "Если уверены, введите цену снова:"
            )
            return

        # Сохранение в БД
        db = next(get_db())
        try:
            old_price = get_setting_value(db, 'priority_price', '500')
            update_setting(db, 'priority_price', str(price))

            # Логирование изменения
            from bot.database.models import AdminLog
            log_entry = AdminLog(
                admin_id=message.from_user.id,
                action='change_priority_price',
                details=f"Изменена цена приоритета: {old_price}₽ → {price}₽"
            )
            db.add(log_entry)
            db.commit()

            await message.answer(
                f"✅ <b>Цена приоритета изменена!</b>\n\n"
                f"Старая цена: {old_price}₽\n"
                f"Новая цена: {price}₽\n\n"
                "Новая цена будет применяться для всех новых приоритетных публикаций.",
                parse_mode="HTML",
                reply_markup=get_admin_menu_keyboard()
            )

            await state.clear()

        finally:
            db.close()

    except ValueError:
        await message.answer("❌ Неверный формат. Введите целое число (например: 500, 1000):")


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
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])
        else:
            posts_text = ""
            for idx, post in enumerate(queue_posts[:10], 1):
                user = post.user
                posts_text += (
                    f"\n{idx}️⃣ {post.product_name[:30]}...\n"
                    f"   От: @{user.username or user.full_name}\n"
                    f"   Позиция: №{post.queue_position}\n"
                )

            remaining = len(queue_posts) - 10
            if remaining > 0:
                posts_text += f"\n... и еще {remaining} постов"

            text = (
                "📋 <b>Очередь публикаций</b>\n\n"
                f"Всего в очереди: {len(queue_posts)} постов\n"
                f"Ближайшие публикации:{posts_text}\n\n"
                "Выберите действие:"
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Список постов", callback_data="admin_queue_list:1")],
                [InlineKeyboardButton(text="📅 Календарь публикаций", callback_data="admin_queue_calendar")],
                [InlineKeyboardButton(text="🗑 Удалить пост", callback_data="admin_queue_delete")],
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_queue_list:"))
async def admin_queue_list_handler(callback: CallbackQuery):
    """Постраничный список постов в очереди"""
    page = int(callback.data.split(':')[1])
    page_size = 5

    db = next(get_db())
    try:
        queue_posts = get_posts_in_queue(db)

        if not queue_posts:
            await callback.answer("Очередь пуста", show_alert=True)
            return

        total_pages = (len(queue_posts) - 1) // page_size + 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_posts = queue_posts[start_idx:end_idx]

        posts_text = ""
        for post in page_posts:
            user = post.user
            posts_text += (
                f"\n📝 <b>{post.product_name[:40]}</b>\n"
                f"   ID: {post.id}\n"
                f"   От: @{user.username or user.full_name}\n"
                f"   Позиция: №{post.queue_position}\n"
                f"   Создан: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

        text = (
            f"📋 <b>Очередь публикаций (стр. {page}/{total_pages})</b>\n\n"
            f"Всего постов: {len(queue_posts)}\n"
            f"{posts_text}\n"
            "Нажмите на ID поста для подробной информации."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []

        # Кнопки постов для просмотра деталей
        for post in page_posts:
            buttons.append([InlineKeyboardButton(
                text=f"ID {post.id}: {post.product_name[:25]}...",
                callback_data=f"admin_post_detail:{post.id}"
            )])

        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_queue_list:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_queue_list:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        buttons.append([InlineKeyboardButton(text="◀️ К очереди", callback_data="admin_queue")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_post_detail:"))
async def admin_post_detail_handler(callback: CallbackQuery):
    """Детальная информация о посте"""
    post_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        from bot.database.models import Post
        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return

        user = post.user

        # Формирование детальной информации
        text = (
            f"📝 <b>Детали поста #{post.id}</b>\n\n"
            f"<b>Товар:</b> {post.product_name}\n"
            f"<b>Статус:</b> {post.status}\n"
            f"<b>Позиция в очереди:</b> №{post.queue_position or 'N/A'}\n\n"
            f"<b>Рекламодатель:</b>\n"
            f"  Имя: {user.full_name}\n"
            f"  Username: @{user.username or 'не указан'}\n"
            f"  ID: {user.telegram_id}\n\n"
            f"<b>Доплата:</b> {post.has_payment or 'Нет'}\n"
            f"<b>Сумма доплаты:</b> {post.payment_amount or 'N/A'}\n"
            f"<b>Маркетплейс:</b> {post.marketplace}\n"
            f"<b>Ожидаемая дата:</b> {post.expected_date or 'Не указана'}\n"
            f"<b>Тематика:</b> {post.blog_theme}\n"
            f"<b>Соцсети:</b> {post.social_networks}\n"
            f"<b>Форматы рекламы:</b> {post.ad_formats or 'N/A'}\n"
            f"<b>Условия:</b> {post.conditions}\n\n"
            f"<b>Создан:</b> {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"<b>Обновлен:</b> {post.updated_at.strftime('%d.%m.%Y %H:%M')}"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить пост", callback_data=f"admin_delete_post:{post.id}")],
            [InlineKeyboardButton(text="◀️ К списку", callback_data="admin_queue_list:1")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_queue_calendar")
async def admin_queue_calendar_handler(callback: CallbackQuery):
    """Календарь публикаций очереди"""
    db = next(get_db())
    try:
        from datetime import datetime, timedelta
        queue_posts = get_posts_in_queue(db)
        posts_per_day = int(get_setting_value(db, 'posts_per_day', '5'))

        if not queue_posts:
            await callback.answer("Очередь пуста", show_alert=True)
            return

        # Расчет примерных дат публикации
        today = datetime.now().date()
        calendar_text = "<b>📅 Примерный календарь публикаций:</b>\n\n"

        current_date = today
        posts_on_date = 0

        for idx, post in enumerate(queue_posts[:20]):
            if posts_on_date >= posts_per_day:
                current_date += timedelta(days=1)
                posts_on_date = 0

            date_str = current_date.strftime('%d.%m.%Y')
            calendar_text += f"{date_str} - {post.product_name[:30]}...\n"
            posts_on_date += 1

        remaining = len(queue_posts) - 20
        if remaining > 0:
            days_remaining = remaining // posts_per_day
            last_date = current_date + timedelta(days=days_remaining)
            calendar_text += f"\n... еще {remaining} постов до {last_date.strftime('%d.%m.%Y')}"

        text = (
            "📅 <b>Календарь очереди</b>\n\n"
            f"Постов в очереди: {len(queue_posts)}\n"
            f"Публикаций в день: {posts_per_day}\n\n"
            f"{calendar_text}\n\n"
            "⚠️ Даты приблизительные и могут измениться"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К очереди", callback_data="admin_queue")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_queue_delete")
async def admin_queue_delete_handler(callback: CallbackQuery):
    """Выбор поста для удаления"""
    db = next(get_db())
    try:
        queue_posts = get_posts_in_queue(db)

        if not queue_posts:
            await callback.answer("Очередь пуста", show_alert=True)
            return

        text = (
            "🗑 <b>Удаление поста из очереди</b>\n\n"
            "Выберите пост для удаления:\n\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []

        for post in queue_posts[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"#{post.id}: {post.product_name[:30]}...",
                callback_data=f"admin_confirm_delete:{post.id}"
            )])

        buttons.append([InlineKeyboardButton(text="◀️ Отменить", callback_data="admin_queue")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_confirm_delete:"))
async def admin_confirm_delete_handler(callback: CallbackQuery):
    """Подтверждение удаления поста"""
    post_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        from bot.database.models import Post
        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return

        text = (
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить пост?\n\n"
            f"<b>ID:</b> {post.id}\n"
            f"<b>Товар:</b> {post.product_name}\n"
            f"<b>От:</b> @{post.user.username or post.user.full_name}\n\n"
            "Это действие нельзя отменить!"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_delete_confirmed:{post.id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_queue")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_delete_confirmed:"))
async def admin_delete_confirmed_handler(callback: CallbackQuery):
    """Окончательное удаление поста"""
    post_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        from bot.database.models import Post, AdminLog
        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return

        post_info = f"{post.id}: {post.product_name}"
        user_info = f"@{post.user.username or post.user.full_name}"

        # Логирование
        log_entry = AdminLog(
            admin_id=callback.from_user.id,
            action='delete_post',
            details=f"Удален пост {post_info} от {user_info}"
        )
        db.add(log_entry)

        # Удаление
        db.delete(post)
        db.commit()

        text = (
            "✅ <b>Пост удален</b>\n\n"
            f"Пост #{post_id} успешно удален из очереди.\n\n"
            "Рекламодатель будет уведомлен об удалении."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К очереди", callback_data="admin_queue")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

        # Уведомление рекламодателя
        try:
            await callback.bot.send_message(
                post.user.telegram_id,
                f"⚠️ Ваш пост '{post.product_name}' был удален администратором из очереди публикаций."
            )
        except:
            pass

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
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])
        else:
            posts_text = ""
            for idx, post in enumerate(priority_posts[:10], 1):
                user = post.user
                posts_text += (
                    f"\n⚡ {post.scheduled_time.strftime('%d.%m в %H:%M')}\n"
                    f"   {post.product_name[:30]}...\n"
                    f"   От: @{user.username or user.full_name}\n"
                )

            remaining = len(priority_posts) - 10
            if remaining > 0:
                posts_text += f"\n... и еще {remaining} постов"

            text = (
                "⚡ <b>Приоритетные публикации</b>\n\n"
                f"Запланировано: {len(priority_posts)} постов\n"
                f"Ближайшие:{posts_text}\n\n"
                "Выберите действие:"
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Список постов", callback_data="admin_priority_list:1")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_priority_stats")],
                [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
            ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_priority_list:"))
async def admin_priority_list_handler(callback: CallbackQuery):
    """Постраничный список приоритетных постов"""
    page = int(callback.data.split(':')[1])
    page_size = 5

    db = next(get_db())
    try:
        priority_posts = get_scheduled_posts(db)

        if not priority_posts:
            await callback.answer("Нет приоритетных постов", show_alert=True)
            return

        total_pages = (len(priority_posts) - 1) // page_size + 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_posts = priority_posts[start_idx:end_idx]

        posts_text = ""
        for post in page_posts:
            user = post.user
            posts_text += (
                f"\n⚡ <b>{post.product_name[:40]}</b>\n"
                f"   ID: {post.id}\n"
                f"   От: @{user.username or user.full_name}\n"
                f"   Запланировано: {post.scheduled_time.strftime('%d.%m.%Y %H:%M')}\n"
            )

        text = (
            f"⚡ <b>Приоритетные публикации (стр. {page}/{total_pages})</b>\n\n"
            f"Всего постов: {len(priority_posts)}\n"
            f"{posts_text}\n"
            "Нажмите на ID поста для подробной информации."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []

        # Кнопки постов для просмотра деталей
        for post in page_posts:
            buttons.append([InlineKeyboardButton(
                text=f"ID {post.id}: {post.product_name[:25]}...",
                callback_data=f"admin_priority_detail:{post.id}"
            )])

        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_priority_list:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_priority_list:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        buttons.append([InlineKeyboardButton(text="◀️ К приоритетным", callback_data="admin_priority")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_priority_detail:"))
async def admin_priority_detail_handler(callback: CallbackQuery):
    """Детальная информация о приоритетном посте"""
    post_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        from bot.database.models import Post, Payment
        post = db.query(Post).filter(Post.id == post_id).first()

        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return

        user = post.user

        # Получение информации об оплате
        payment = db.query(Payment).filter(Payment.post_id == post.id).first()

        payment_info = "Не найдена"
        if payment:
            payment_info = (
                f"{payment.amount}₽\n"
                f"   Статус: {payment.status}\n"
                f"   Дата: {payment.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

        # Формирование детальной информации
        text = (
            f"⚡ <b>Приоритетный пост #{post.id}</b>\n\n"
            f"<b>Товар:</b> {post.product_name}\n"
            f"<b>Статус:</b> {post.status}\n"
            f"<b>Запланировано:</b> {post.scheduled_time.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"<b>💳 Оплата:</b>\n{payment_info}\n\n"
            f"<b>Рекламодатель:</b>\n"
            f"  Имя: {user.full_name}\n"
            f"  Username: @{user.username or 'не указан'}\n"
            f"  ID: {user.telegram_id}\n\n"
            f"<b>Доплата:</b> {post.has_payment or 'Нет'}\n"
            f"<b>Сумма доплаты:</b> {post.payment_amount or 'N/A'}\n"
            f"<b>Маркетплейс:</b> {post.marketplace}\n"
            f"<b>Ожидаемая дата:</b> {post.expected_date or 'Не указана'}\n"
            f"<b>Тематика:</b> {post.blog_theme}\n"
            f"<b>Соцсети:</b> {post.social_networks}\n"
            f"<b>Форматы рекламы:</b> {post.ad_formats or 'N/A'}\n"
            f"<b>Условия:</b> {post.conditions}\n\n"
            f"<b>Создан:</b> {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"<b>Обновлен:</b> {post.updated_at.strftime('%d.%m.%Y %H:%M')}"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К списку", callback_data="admin_priority_list:1")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_priority_stats")
async def admin_priority_stats_handler(callback: CallbackQuery):
    """Статистика приоритетных публикаций"""
    db = next(get_db())
    try:
        from bot.database.models import Post, Payment
        from datetime import datetime, timedelta

        # Все приоритетные посты
        priority_posts = get_scheduled_posts(db)

        # Опубликованные приоритетные
        published_priority = db.query(Post).filter(
            Post.status == 'published',
            Post.scheduled_time.isnot(None)
        ).count()

        # Оплаты за последний месяц
        month_ago = datetime.now() - timedelta(days=30)
        recent_payments = db.query(Payment).filter(
            Payment.created_at >= month_ago,
            Payment.status == 'completed'
        ).all()

        total_revenue = sum(p.amount for p in recent_payments)
        payments_count = len(recent_payments)

        # Средняя цена
        avg_price = total_revenue / payments_count if payments_count > 0 else 0

        text = (
            "📊 <b>Статистика приоритетных публикаций</b>\n\n"
            "<b>Запланировано:</b>\n"
            f"  Всего: {len(priority_posts)} постов\n\n"
            "<b>За все время:</b>\n"
            f"  Опубликовано: {published_priority} постов\n\n"
            "<b>За последние 30 дней:</b>\n"
            f"  💰 Оплат: {payments_count}\n"
            f"  💵 Доход: {total_revenue}₽\n"
            f"  📊 Средний чек: {avg_price:.0f}₽\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К приоритетным", callback_data="admin_priority")]
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
            f"⚡ Запланировано: {priority_posts} постов\n\n"
            "Выберите действие:"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Детальная статистика", callback_data="admin_stats_detailed")],
            [InlineKeyboardButton(text="📅 Статистика по периодам", callback_data="admin_stats_period")],
            [InlineKeyboardButton(text="💰 Финансовая статистика", callback_data="admin_stats_financial")],
            [InlineKeyboardButton(text="📥 Экспорт отчета", callback_data="admin_stats_export")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_stats_detailed")
async def admin_stats_detailed_handler(callback: CallbackQuery):
    """Детальная статистика"""
    db = next(get_db())
    try:
        from bot.database.models import User, Post, Payment
        from datetime import datetime, timedelta

        # Общая статистика
        total_users = db.query(User).count()
        advertisers = db.query(User).filter(User.role == 'advertiser').count()

        # Посты
        all_posts = db.query(Post).count()
        published = db.query(Post).filter(Post.status == 'published').count()
        in_queue = db.query(Post).filter(Post.status == 'queue').count()
        scheduled = db.query(Post).filter(Post.status == 'scheduled').count()

        # Активность за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
        new_posts_week = db.query(Post).filter(Post.created_at >= week_ago).count()
        published_week = db.query(Post).filter(
            Post.status == 'published',
            Post.updated_at >= week_ago
        ).count()

        # Платежи
        total_payments = db.query(Payment).filter(Payment.status == 'completed').count()
        total_revenue = sum(p.amount for p in db.query(Payment).filter(Payment.status == 'completed').all())

        text = (
            "📈 <b>Детальная статистика</b>\n\n"
            "<b>👥 Пользователи:</b>\n"
            f"  Всего: {total_users}\n"
            f"  Рекламодателей: {advertisers}\n"
            f"  Новых за неделю: {new_users_week}\n\n"
            "<b>📝 Посты:</b>\n"
            f"  Всего создано: {all_posts}\n"
            f"  Опубликовано: {published}\n"
            f"  В очереди: {in_queue}\n"
            f"  Запланировано: {scheduled}\n"
            f"  Создано за неделю: {new_posts_week}\n"
            f"  Опубликовано за неделю: {published_week}\n\n"
            "<b>💰 Финансы:</b>\n"
            f"  Платежей: {total_payments}\n"
            f"  Доход: {total_revenue}₽\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К статистике", callback_data="admin_stats")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_stats_period")
async def admin_stats_period_handler(callback: CallbackQuery):
    """Выбор периода для статистики"""
    text = (
        "📅 <b>Статистика по периодам</b>\n\n"
        "Выберите период для просмотра статистики:"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За 7 дней", callback_data="admin_stats_period:7")],
        [InlineKeyboardButton(text="За 30 дней", callback_data="admin_stats_period:30")],
        [InlineKeyboardButton(text="За 90 дней", callback_data="admin_stats_period:90")],
        [InlineKeyboardButton(text="За всё время", callback_data="admin_stats_period:all")],
        [InlineKeyboardButton(text="◀️ К статистике", callback_data="admin_stats")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_stats_period:"))
async def admin_stats_period_data_handler(callback: CallbackQuery):
    """Статистика за выбранный период"""
    period = callback.data.split(':')[1]

    db = next(get_db())
    try:
        from bot.database.models import User, Post, Payment
        from datetime import datetime, timedelta

        # Определение периода
        if period == 'all':
            period_start = datetime(2020, 1, 1)
            period_name = "все время"
        else:
            days = int(period)
            period_start = datetime.now() - timedelta(days=days)
            period_name = f"{days} дней"

        # Статистика за период
        new_users = db.query(User).filter(User.created_at >= period_start).count()
        new_posts = db.query(Post).filter(Post.created_at >= period_start).count()
        published_posts = db.query(Post).filter(
            Post.status == 'published',
            Post.updated_at >= period_start
        ).count()

        # Финансы
        payments = db.query(Payment).filter(
            Payment.created_at >= period_start,
            Payment.status == 'completed'
        ).all()

        revenue = sum(p.amount for p in payments)
        payments_count = len(payments)
        avg_payment = revenue / payments_count if payments_count > 0 else 0

        # Расчет среднего в день
        if period == 'all':
            days_count = (datetime.now() - period_start).days
        else:
            days_count = int(period)

        posts_per_day = published_posts / days_count if days_count > 0 else 0
        revenue_per_day = revenue / days_count if days_count > 0 else 0

        text = (
            f"📅 <b>Статистика за {period_name}</b>\n\n"
            "<b>👥 Пользователи:</b>\n"
            f"  Новых: {new_users}\n\n"
            "<b>📝 Посты:</b>\n"
            f"  Создано: {new_posts}\n"
            f"  Опубликовано: {published_posts}\n"
            f"  В среднем в день: {posts_per_day:.1f}\n\n"
            "<b>💰 Финансы:</b>\n"
            f"  Платежей: {payments_count}\n"
            f"  Доход: {revenue}₽\n"
            f"  Средний чек: {avg_payment:.0f}₽\n"
            f"  Доход в день: {revenue_per_day:.0f}₽\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Выбрать период", callback_data="admin_stats_period")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_stats_financial")
async def admin_stats_financial_handler(callback: CallbackQuery):
    """Финансовая статистика"""
    db = next(get_db())
    try:
        from bot.database.models import Payment
        from datetime import datetime, timedelta

        # Все платежи
        all_payments = db.query(Payment).filter(Payment.status == 'completed').all()
        total_revenue = sum(p.amount for p in all_payments)

        # За месяц
        month_ago = datetime.now() - timedelta(days=30)
        month_payments = [p for p in all_payments if p.created_at >= month_ago]
        month_revenue = sum(p.amount for p in month_payments)

        # За неделю
        week_ago = datetime.now() - timedelta(days=7)
        week_payments = [p for p in all_payments if p.created_at >= week_ago]
        week_revenue = sum(p.amount for p in week_payments)

        # Средние показатели
        avg_all = total_revenue / len(all_payments) if all_payments else 0
        avg_month = month_revenue / len(month_payments) if month_payments else 0

        text = (
            "💰 <b>Финансовая статистика</b>\n\n"
            "<b>За все время:</b>\n"
            f"  Платежей: {len(all_payments)}\n"
            f"  Доход: {total_revenue}₽\n"
            f"  Средний чек: {avg_all:.0f}₽\n\n"
            "<b>За последние 30 дней:</b>\n"
            f"  Платежей: {len(month_payments)}\n"
            f"  Доход: {month_revenue}₽\n"
            f"  Средний чек: {avg_month:.0f}₽\n\n"
            "<b>За последние 7 дней:</b>\n"
            f"  Платежей: {len(week_payments)}\n"
            f"  Доход: {week_revenue}₽\n"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К статистике", callback_data="admin_stats")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data == "admin_stats_export")
async def admin_stats_export_handler(callback: CallbackQuery):
    """Экспорт статистики"""
    await callback.answer("Формирование отчета...", show_alert=False)

    db = next(get_db())
    try:
        from bot.database.models import User, Post, Payment
        from datetime import datetime
        import csv
        from io import StringIO

        # Сбор данных
        users = db.query(User).all()
        posts = db.query(Post).all()
        payments = db.query(Payment).filter(Payment.status == 'completed').all()

        # Создание CSV
        output = StringIO()
        writer = csv.writer(output)

        # Общая статистика
        writer.writerow(['=== ОБЩАЯ СТАТИСТИКА ==='])
        writer.writerow(['Дата формирования', datetime.now().strftime('%d.%m.%Y %H:%M')])
        writer.writerow([])

        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего пользователей', len(users)])
        writer.writerow(['Рекламодателей', len([u for u in users if u.role == 'advertiser'])])
        writer.writerow(['Всего постов', len(posts)])
        writer.writerow(['Опубликовано', len([p for p in posts if p.status == 'published'])])
        writer.writerow(['В очереди', len([p for p in posts if p.status == 'queue'])])
        writer.writerow([])

        # Финансы
        writer.writerow(['=== ФИНАНСОВАЯ СТАТИСТИКА ==='])
        writer.writerow(['Всего платежей', len(payments)])
        writer.writerow(['Общий доход', f"{sum(p.amount for p in payments)}₽"])
        writer.writerow(['Средний чек', f"{sum(p.amount for p in payments) / len(payments) if payments else 0:.0f}₽"])
        writer.writerow([])

        # Список постов
        writer.writerow(['=== СПИСОК ПОСТОВ ==='])
        writer.writerow(['ID', 'Товар', 'Статус', 'Создан', 'Рекламодатель'])
        for post in posts:
            writer.writerow([
                post.id,
                post.product_name,
                post.status,
                post.created_at.strftime('%d.%m.%Y %H:%M'),
                post.user.username or post.user.full_name
            ])

        # Отправка файла
        csv_data = output.getvalue()
        from aiogram.types import BufferedInputFile

        file = BufferedInputFile(
            csv_data.encode('utf-8-sig'),
            filename=f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        await callback.bot.send_document(
            callback.from_user.id,
            file,
            caption="📊 Экспорт статистики бота"
        )

        await callback.answer("✅ Отчет сформирован и отправлен", show_alert=True)

    except Exception as e:
        await callback.answer(f"❌ Ошибка при формировании отчета: {str(e)}", show_alert=True)

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
