from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from bot.database import get_db
from bot.database.crud import create_post, get_user_by_telegram_id, get_next_queue_position, get_setting_value
from bot.states.post_states import PostCreation
from bot.keyboards.post_creator import (
    get_skip_cancel_keyboard,
    get_payment_keyboard,
    get_marketplace_keyboard,
    get_expected_date_keyboard,
    get_blog_theme_keyboard,
    get_social_networks_keyboard,
    get_conditions_keyboard,
    get_preview_keyboard,
    get_back_cancel_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard, get_admin_menu_keyboard
from bot.config import config

router = Router()


# ===== НАЧАЛО СОЗДАНИЯ ПОСТА =====

@router.message(F.text == "📝 Создать пост")
async def create_post_start(message: Message, state: FSMContext):
    """Начало создания поста"""
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("❌ Ошибка: пользователь не найден. Отправьте /start для регистрации.")
            return

        # ВАЖНО: Очистка любого предыдущего состояния
        current_state = await state.get_state()
        if current_state:
            await state.clear()

        text = (
            "📝 <b>Создание нового поста</b>\n\n"
            "Шаг 1 из 8: Загрузка изображения\n\n"
            "Отправьте изображение товара или услуги.\n\n"
            "Требования:\n"
            "• Формат: JPG, PNG\n"
            "• Размер: до 10 МБ\n"
            "• Качество: хорошее освещение, четкое изображение"
        )

        await message.answer(text, reply_markup=get_skip_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.image)

    finally:
        db.close()


# ===== ШАГ 1: ИЗОБРАЖЕНИЕ =====

@router.message(PostCreation.image, F.photo)
async def process_image(message: Message, state: FSMContext):
    """Обработка изображения"""
    photo = message.photo[-1]

    await state.update_data(image_file_id=photo.file_id)

    text = (
        "✅ Изображение загружено!\n\n"
        "Шаг 2 из 8: Название товара\n\n"
        "Введите название товара или услуги (до 100 символов):"
    )

    await message.answer(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.product_name)


@router.callback_query(PostCreation.image, F.data == "skip")
async def skip_image(callback: CallbackQuery, state: FSMContext):
    """Пропуск изображения"""
    await callback.answer()

    text = (
        "⏭ Изображение пропущено\n\n"
        "Шаг 2 из 8: Название товара\n\n"
        "Введите название товара или услуги (до 100 символов):"
    )

    await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.product_name)


# ===== ШАГ 2: НАЗВАНИЕ ТОВАРА =====

@router.message(PostCreation.product_name, F.text)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия товара"""
    product_name = message.text.strip()

    if len(product_name) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов. Попробуйте еще раз:")
        return

    await state.update_data(product_name=product_name)

    text = (
        "✅ Название сохранено!\n\n"
        "Шаг 3 из 8: Доплата\n\n"
        "Требуется ли доплата за товар?"
    )

    await message.answer(text, reply_markup=get_payment_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.payment)


# ===== ШАГ 3: ДОПЛАТА =====

@router.callback_query(PostCreation.payment, F.data == "payment_no")
async def process_payment_no(callback: CallbackQuery, state: FSMContext):
    """Нет доплаты"""
    await callback.answer()

    await state.update_data(payment="Нет")

    text = (
        "✅ Доплата: Нет\n\n"
        "Шаг 4 из 8: Маркетплейс\n\n"
        "Выберите маркетплейс, на котором продается товар:"
    )

    await callback.message.edit_text(text, reply_markup=get_marketplace_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.marketplace)


@router.callback_query(PostCreation.payment, F.data == "payment_yes")
async def process_payment_yes(callback: CallbackQuery, state: FSMContext):
    """Есть доплата"""
    await callback.answer()

    await state.update_data(payment="Есть доплата")

    text = (
        "Укажите сумму доплаты (в рублях):\n\n"
        "Например: 500"
    )

    await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.payment_amount)


@router.callback_query(PostCreation.payment, F.data == "payment_discuss")
async def process_payment_discuss(callback: CallbackQuery, state: FSMContext):
    """Доплата обсуждается"""
    await callback.answer()

    await state.update_data(payment="Обсуждается")

    text = (
        "✅ Доплата: Обсуждается\n\n"
        "Шаг 4 из 8: Маркетплейс\n\n"
        "Выберите маркетплейс, на котором продается товар:"
    )

    await callback.message.edit_text(text, reply_markup=get_marketplace_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.marketplace)


@router.message(PostCreation.payment_amount, F.text)
async def process_payment_amount(message: Message, state: FSMContext):
    """Обработка суммы доплаты"""
    try:
        amount = int(message.text.strip())

        if amount < 0:
            await message.answer("❌ Сумма не может быть отрицательной. Попробуйте еще раз:")
            return

        await state.update_data(payment_amount=str(amount))

        text = (
            f"✅ Сумма доплаты: {amount}₽\n\n"
            "Шаг 4 из 8: Маркетплейс\n\n"
            "Выберите маркетплейс, на котором продается товар:"
        )

        await message.answer(text, reply_markup=get_marketplace_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.marketplace)

    except ValueError:
        await message.answer("❌ Неверный формат. Введите целое число (например: 500):")


# ===== ШАГ 4: МАРКЕТПЛЕЙС =====

@router.callback_query(PostCreation.marketplace, F.data.startswith("marketplace_"))
async def process_marketplace(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора маркетплейса"""
    await callback.answer()

    marketplace_map = {
        "marketplace_wb": "Wildberries",
        "marketplace_ozon": "Ozon",
        "marketplace_na": "Не применимо",
        "marketplace_other": "custom"
    }

    marketplace = marketplace_map.get(callback.data)

    if marketplace == "custom":
        text = "Введите название маркетплейса:"

        await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.marketplace_custom)
    else:
        await state.update_data(marketplace=marketplace)

        text = (
            f"✅ Маркетплейс: {marketplace}\n\n"
            "Шаг 5 из 8: Ожидаемая дата публикации\n\n"
            "Укажите, когда вы хотите опубликовать пост:"
        )

        await callback.message.edit_text(text, reply_markup=get_expected_date_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.expected_date)


@router.message(PostCreation.marketplace_custom, F.text)
async def process_marketplace_custom(message: Message, state: FSMContext):
    """Обработка названия маркетплейса"""
    marketplace = message.text.strip()

    await state.update_data(marketplace=marketplace)

    text = (
        f"✅ Маркетплейс: {marketplace}\n\n"
        "Шаг 5 из 8: Ожидаемая дата публикации\n\n"
        "Укажите, когда вы хотите опубликовать пост:"
    )

    await message.answer(text, reply_markup=get_expected_date_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.expected_date)


# ===== ШАГ 5: ОЖИДАЕМАЯ ДАТА =====

@router.callback_query(PostCreation.expected_date, F.data.startswith("date_"))
async def process_expected_date(callback: CallbackQuery, state: FSMContext):
    """Обработка ожидаемой даты"""
    await callback.answer()

    date_map = {
        "date_any": "Любая дата",
        "date_specific": "custom_specific",
        "date_period": "custom_period"
    }

    date_choice = date_map.get(callback.data)

    if date_choice in ["custom_specific", "custom_period"]:
        text = "Введите дату в формате ДД.ММ.ГГГГ\n\nНапример: 15.12.2024"

        await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.expected_date_custom)
    else:
        await state.update_data(expected_date=date_choice)

        text = (
            f"✅ Дата публикации: {date_choice}\n\n"
            "Шаг 6 из 8: Тематика блога\n\n"
            "Выберите желаемую тематику блога для размещения:"
        )

        await callback.message.edit_text(text, reply_markup=get_blog_theme_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.blog_theme)


@router.message(PostCreation.expected_date_custom, F.text)
async def process_expected_date_custom(message: Message, state: FSMContext):
    """Обработка конкретной даты"""
    date_text = message.text.strip()

    # Базовая валидация формата
    import re
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_text):
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.12.2024):")
        return

    await state.update_data(expected_date=date_text)

    text = (
        f"✅ Дата публикации: {date_text}\n\n"
        "Шаг 6 из 8: Тематика блога\n\n"
        "Выберите желаемую тематику блога для размещения:"
    )

    await message.answer(text, reply_markup=get_blog_theme_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.blog_theme)


# ===== ШАГ 6: ТЕМАТИКА БЛОГА =====

@router.callback_query(PostCreation.blog_theme, F.data.startswith("theme_"))
async def process_blog_theme(callback: CallbackQuery, state: FSMContext):
    """Обработка тематики блога"""
    await callback.answer()

    theme_map = {
        "theme_female": "Все тематики с женской ЦА",
        "theme_male": "Все тематики с мужской ЦА",
        "theme_child": "Детская тематика",
        "theme_any": "Любая тематика",
        "theme_custom": "custom"
    }

    theme = theme_map.get(callback.data)

    if theme == "custom":
        text = "Введите свою тематику:"

        await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.blog_theme_custom)
    else:
        await state.update_data(blog_theme=theme)

        text = (
            f"✅ Тематика: {theme}\n\n"
            "Шаг 7 из 8: Социальные сети\n\n"
            "Выберите социальные сети для размещения (можно несколько):"
        )

        await callback.message.edit_text(text, reply_markup=get_social_networks_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.social_networks)
        await state.update_data(selected_networks=[])


@router.message(PostCreation.blog_theme_custom, F.text)
async def process_blog_theme_custom(message: Message, state: FSMContext):
    """Обработка своей тематики"""
    theme = message.text.strip()

    await state.update_data(blog_theme=theme)

    text = (
        f"✅ Тематика: {theme}\n\n"
        "Шаг 7 из 8: Социальные сети\n\n"
        "Выберите социальные сети для размещения (можно несколько):"
    )

    await message.answer(text, reply_markup=get_social_networks_keyboard(), parse_mode="HTML")
    await state.set_state(PostCreation.social_networks)
    await state.update_data(selected_networks=[])


# ===== ШАГ 7: СОЦИАЛЬНЫЕ СЕТИ =====

@router.callback_query(PostCreation.social_networks, F.data.startswith("sn_"))
async def process_social_networks(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора социальных сетей"""

    data = await state.get_data()
    selected = data.get('selected_networks', [])

    network_map = {
        "sn_instagram": "Instagram",
        "sn_tiktok": "TikTok",
        "sn_telegram": "Telegram",
        "sn_vk": "VK",
        "sn_youtube": "YouTube"
    }

    if callback.data == "sn_continue":
        if not selected:
            await callback.answer("Выберите хотя бы одну социальную сеть", show_alert=True)
            return

        await callback.answer()

        networks_str = ", ".join(selected)
        await state.update_data(social_networks=networks_str)

        text = (
            f"✅ Социальные сети: {networks_str}\n\n"
            "Шаг 8 из 8: Условия сотрудничества\n\n"
            "Выберите условия сотрудничества (можно несколько):"
        )

        await callback.message.edit_text(text, reply_markup=get_conditions_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.conditions)
        await state.update_data(selected_conditions=[])
    else:
        network = network_map.get(callback.data)

        if network:
            if network in selected:
                selected.remove(network)
            else:
                selected.append(network)

            await state.update_data(selected_networks=selected)
            await callback.message.edit_reply_markup(reply_markup=get_social_networks_keyboard(selected))
            await callback.answer()


# ===== ШАГ 8: УСЛОВИЯ СОТРУДНИЧЕСТВА =====

@router.callback_query(PostCreation.conditions, F.data.startswith("cond_"))
async def process_conditions(callback: CallbackQuery, state: FSMContext):
    """Обработка условий сотрудничества"""

    data = await state.get_data()
    selected = data.get('selected_conditions', [])

    condition_map = {
        "cond_search": "Заказ товара по поисковому запросу",
        "cond_pickup": "Выкуп с ПВЗ",
        "cond_review": "Положительный отзыв 5⭐",
        "cond_video": "Съемка видео по ТЗ",
        "cond_keep": "Не удалять контент"
    }

    if callback.data == "cond_custom":
        await callback.answer()

        text = "Введите свои условия сотрудничества:"

        await callback.message.edit_text(text, reply_markup=get_back_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PostCreation.conditions_custom)

    elif callback.data == "cond_continue":
        if not selected:
            await callback.answer("Выберите хотя бы одно условие", show_alert=True)
            return

        await callback.answer()

        conditions_str = "\n• ".join(selected)
        await state.update_data(conditions=conditions_str)

        # Переход к предпросмотру
        await show_preview(callback.message, state)

    else:
        condition = condition_map.get(callback.data)

        if condition:
            if condition in selected:
                selected.remove(condition)
            else:
                selected.append(condition)

            await state.update_data(selected_conditions=selected)
            await callback.message.edit_reply_markup(reply_markup=get_conditions_keyboard(selected))
            await callback.answer()


@router.message(PostCreation.conditions_custom, F.text)
async def process_conditions_custom(message: Message, state: FSMContext):
    """Обработка своих условий"""
    conditions = message.text.strip()

    await state.update_data(conditions=conditions)

    # Переход к предпросмотру
    await show_preview(message, state)


# ===== ПРЕДПРОСМОТР =====

async def show_preview(message_or_callback, state: FSMContext):
    """Показ предпросмотра поста"""
    data = await state.get_data()

    # Получаем telegram_id для проверки прав администратора
    if isinstance(message_or_callback, Message):
        telegram_id = message_or_callback.from_user.id
    else:
        telegram_id = message_or_callback.from_user.id

    is_admin = config.is_admin(telegram_id)

    # Формирование текста предпросмотра
    text = "📋 <b>Предпросмотр поста</b>\n\n"

    text += f"<b>Товар:</b> {data.get('product_name', 'Не указано')}\n"
    text += f"<b>Доплата:</b> {data.get('payment', 'Не указано')}"

    if data.get('payment_amount'):
        text += f" ({data['payment_amount']}₽)"

    text += f"\n<b>Маркетплейс:</b> {data.get('marketplace', 'Не указано')}\n"
    text += f"<b>Дата публикации:</b> {data.get('expected_date', 'Не указано')}\n"
    text += f"<b>Тематика:</b> {data.get('blog_theme', 'Не указано')}\n"
    text += f"<b>Социальные сети:</b> {data.get('social_networks', 'Не указано')}\n"
    text += f"<b>Условия:</b>\n• {data.get('conditions', 'Не указано')}\n\n"

    text += "Выберите тип публикации:"

    await state.set_state(PostCreation.preview)

    if isinstance(message_or_callback, Message):
        # Если есть изображение, отправляем с ним
        if data.get('image_file_id'):
            await message_or_callback.answer_photo(
                photo=data['image_file_id'],
                caption=text,
                reply_markup=get_preview_keyboard(is_admin=is_admin),
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer(
                text,
                reply_markup=get_preview_keyboard(is_admin=is_admin),
                parse_mode="HTML"
            )
    else:
        # Для callback просто редактируем текст
        await message_or_callback.edit_text(
            text,
            reply_markup=get_preview_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )


# ===== ПУБЛИКАЦИЯ =====

@router.callback_query(PostCreation.preview, F.data == "publish_queue")
async def publish_to_queue(callback: CallbackQuery, state: FSMContext):
    """Публикация в очередь"""
    await callback.answer()

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        data = await state.get_data()

        # Получение следующей позиции в очереди
        queue_position = get_next_queue_position(db)

        # Создание поста
        # Преобразуем social_networks в список
        social_networks_str = data.get('social_networks', '')
        social_networks_list = [sn.strip() for sn in social_networks_str.split(',') if sn.strip()]

        post_data = {
            'user_id': user.id,
            'product_name': data.get('product_name'),
            'has_payment': data.get('payment'),  # Исправлено: payment -> has_payment
            'payment_amount': data.get('payment_amount'),
            'marketplace': data.get('marketplace'),
            'expected_date': data.get('expected_date'),
            'blog_theme': data.get('blog_theme'),
            'social_networks': social_networks_list,  # Передаем как список
            'ad_formats': data.get('ad_formats'),
            'conditions': data.get('conditions'),
            'image_file_id': data.get('image_file_id'),
            'status': 'queue',
            'queue_position': queue_position
        }

        post = create_post(db, **post_data)

        # Получение цены очереди
        queue_price = get_setting_value(db, 'queue_price', '0')

        # Расчет примерного времени публикации
        from datetime import datetime, timedelta
        posts_per_day = int(get_setting_value(db, 'posts_per_day', '5'))
        schedule_times = get_setting_value(db, 'schedule_times', '10:00,13:00,16:00,19:00,22:00')

        # Вычисляем на какой день попадает пост
        days_ahead = (queue_position - 1) // posts_per_day
        post_index_in_day = (queue_position - 1) % posts_per_day

        # Получаем время публикации
        times_list = [t.strip() for t in schedule_times.split(',')]
        if post_index_in_day < len(times_list):
            pub_time = times_list[post_index_in_day]
        else:
            pub_time = times_list[-1]

        # Рассчитываем дату
        pub_date = datetime.now().date() + timedelta(days=days_ahead)
        estimated_time = f"{pub_date.strftime('%d.%m.%Y')} в {pub_time}"

        text = (
            "✅ <b>Пост добавлен в очередь!</b>\n\n"
            f"Позиция в очереди: №{queue_position}\n"
            f"Примерное время публикации: {estimated_time}\n"
            f"Стоимость публикации: {queue_price}₽\n\n"
            "📢 Пост будет автоматически опубликован в канале по расписанию.\n"
            "Вы можете отслеживать статус в разделе 'Мои публикации'."
        )

        # Определяем клавиатуру в зависимости от роли
        keyboard = get_admin_menu_keyboard() if config.is_admin(user.telegram_id) else get_main_menu_keyboard()

        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        # Удаляем предыдущее сообщение с предпросмотром
        try:
            await callback.message.delete()
        except:
            pass

        await state.clear()

    finally:
        db.close()


@router.callback_query(PostCreation.preview, F.data == "publish_priority")
async def publish_priority(callback: CallbackQuery, state: FSMContext):
    """Приоритетная публикация"""
    await callback.answer()

    db = next(get_db())
    try:
        priority_price = get_setting_value(db, 'priority_price', '500')

        text = (
            "⚡ <b>Приоритетная публикация</b>\n\n"
            f"Стоимость: {priority_price}₽\n\n"
            "Преимущества:\n"
            "• Публикация в выбранное вами время\n"
            "• Гарантированное размещение\n"
            "• Приоритет над обычной очередью\n\n"
            "⚠️ Функционал оплаты будет добавлен позже.\n"
            "Пока вы можете опубликовать пост в обычной очереди.\n\n"
            "Вернуться к выбору?"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕐 Опубликовать в очереди", callback_data="publish_queue")],
            [InlineKeyboardButton(text="💾 Сохранить в черновики", callback_data="save_draft")],
            [InlineKeyboardButton(text="◀️ Назад к предпросмотру", callback_data="back_to_preview")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(PostCreation.preview, F.data == "back_to_preview")
async def back_to_preview(callback: CallbackQuery, state: FSMContext):
    """Возврат к предпросмотру"""
    await callback.answer()
    await show_preview(callback.message, state)


@router.callback_query(PostCreation.preview, F.data == "publish_now")
async def publish_now(callback: CallbackQuery, state: FSMContext):
    """Немедленная публикация (только для админов)"""
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)

        # Проверка прав администратора
        if not config.is_admin(user.telegram_id):
            await callback.answer("❌ Доступно только администраторам", show_alert=True)
            return

        await callback.answer()

        data = await state.get_data()

        # Получение ID канала из настроек
        from bot.database.crud import get_setting_value
        channel_id = get_setting_value(db, 'channel_id')

        if not channel_id:
            await callback.message.answer(
                "❌ <b>Ошибка!</b>\n\n"
                "ID канала не настроен. Настройте канал в админ-панели.",
                parse_mode="HTML"
            )
            return

        # Формирование текста поста
        from bot.utils.post_formatter import format_post_for_channel
        post_data = {
            'product_name': data.get('product_name'),
            'has_payment': data.get('payment'),
            'payment_amount': data.get('payment_amount'),
            'marketplace': data.get('marketplace'),
            'expected_date': data.get('expected_date'),
            'blog_theme': data.get('blog_theme'),
            'social_networks': [sn.strip() for sn in data.get('social_networks', '').split(',') if sn.strip()],
            'ad_formats': data.get('ad_formats'),
            'conditions': data.get('conditions'),
        }

        text = format_post_for_channel(post_data)

        # Отправка в канал
        from aiogram import Bot
        bot = Bot(token=config.BOT_TOKEN)

        try:
            if data.get('image_file_id'):
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=data['image_file_id'],
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    parse_mode="HTML"
                )

            # Сохранение поста в базу со статусом published
            social_networks_str = data.get('social_networks', '')
            social_networks_list = [sn.strip() for sn in social_networks_str.split(',') if sn.strip()]

            from datetime import datetime
            post_db_data = {
                'user_id': user.id,
                'product_name': data.get('product_name'),
                'has_payment': data.get('payment'),
                'payment_amount': data.get('payment_amount'),
                'marketplace': data.get('marketplace'),
                'expected_date': data.get('expected_date'),
                'blog_theme': data.get('blog_theme'),
                'social_networks': social_networks_list,
                'ad_formats': data.get('ad_formats'),
                'conditions': data.get('conditions'),
                'image_file_id': data.get('image_file_id'),
                'status': 'published',
                'published_at': datetime.now()
            }

            post = create_post(db, **post_db_data)

            text = (
                "✅ <b>Пост успешно опубликован!</b>\n\n"
                f"Пост #{post.id} был немедленно опубликован в канале.\n\n"
                "Вы можете просмотреть его в разделе 'Мои публикации'."
            )

            keyboard = get_admin_menu_keyboard() if config.is_admin(user.telegram_id) else get_main_menu_keyboard()
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

            try:
                await callback.message.delete()
            except:
                pass

            await state.clear()

        except Exception as e:
            await callback.message.answer(
                f"❌ <b>Ошибка при публикации!</b>\n\n"
                f"Не удалось опубликовать пост в канал.\n"
                f"Ошибка: {str(e)}",
                parse_mode="HTML"
            )

        finally:
            await bot.session.close()

    finally:
        db.close()


@router.callback_query(PostCreation.preview, F.data == "save_draft")
async def save_draft(callback: CallbackQuery, state: FSMContext):
    """Сохранение в черновики"""
    await callback.answer()

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        data = await state.get_data()

        # Преобразуем social_networks в список
        social_networks_str = data.get('social_networks', '')
        social_networks_list = [sn.strip() for sn in social_networks_str.split(',') if sn.strip()]

        post_data = {
            'user_id': user.id,
            'product_name': data.get('product_name'),
            'has_payment': data.get('payment'),
            'payment_amount': data.get('payment_amount'),
            'marketplace': data.get('marketplace'),
            'expected_date': data.get('expected_date'),
            'blog_theme': data.get('blog_theme'),
            'social_networks': social_networks_list,
            'ad_formats': data.get('ad_formats'),
            'conditions': data.get('conditions'),
            'image_file_id': data.get('image_file_id'),
            'status': 'draft'
        }

        post = create_post(db, **post_data)

        text = (
            "💾 <b>Пост сохранен в черновики!</b>\n\n"
            f"ID черновика: #{post.id}\n\n"
            "Вы можете завершить и опубликовать его позже в разделе 'Мои черновики'."
        )

        keyboard = get_admin_menu_keyboard() if config.is_admin(user.telegram_id) else get_main_menu_keyboard()

        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        try:
            await callback.message.delete()
        except:
            pass

        await state.clear()

    finally:
        db.close()


# ===== РЕДАКТИРОВАНИЕ И НАВИГАЦИЯ =====

@router.callback_query(PostCreation.preview, F.data == "edit_post")
async def edit_post_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование поста (функция в разработке)"""
    await callback.answer(
        "⚠️ Функция редактирования будет добавлена в следующем обновлении.\n"
        "Пока вы можете отменить создание и начать заново, или сохранить в черновики.",
        show_alert=True
    )


@router.callback_query(F.data == "back")
async def back_button_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' (функция в разработке)"""
    await callback.answer(
        "⚠️ Навигация 'Назад' будет добавлена в следующем обновлении.\n"
        "Пока вы можете отменить создание и начать заново.",
        show_alert=True
    )


# ===== ОТМЕНА СОЗДАНИЯ =====

@router.callback_query(F.data == "cancel_post")
async def cancel_post_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания поста"""
    await callback.answer()

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        keyboard = get_admin_menu_keyboard() if config.is_admin(user.telegram_id) else get_main_menu_keyboard()

        await callback.message.answer(
            "❌ Создание поста отменено.",
            reply_markup=keyboard
        )

        try:
            await callback.message.delete()
        except:
            pass

        await state.clear()

    finally:
        db.close()
