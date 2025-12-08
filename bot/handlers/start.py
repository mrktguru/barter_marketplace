from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session

from bot.config import config
from bot.database import get_db
from bot.database.crud import get_user_by_telegram_id, create_user
from bot.keyboards.main_menu import get_main_menu_keyboard, get_admin_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Получение сессии БД
    db = next(get_db())
    try:
        # Проверка существования пользователя
        user = get_user_by_telegram_id(db, telegram_id)

        if not user:
            # Определение роли
            role = 'admin' if config.is_admin(telegram_id) else 'advertiser'

            # Создание нового пользователя
            user = create_user(
                db=db,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role
            )

            if role == 'admin':
                await message.answer(
                    f"👋 Добро пожаловать, администратор!\n\n"
                    f"Вы получили доступ к панели администратора.",
                    reply_markup=get_admin_menu_keyboard()
                )
            else:
                await message.answer(
                    f"👋 Добро пожаловать в бартерный канал для блоггеров!\n\n"
                    f"Здесь вы можете размещать свои предложения для блоггеров.\n\n"
                    f"Выберите действие из меню:",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            # Пользователь уже существует
            if user.role == 'admin':
                await message.answer(
                    f"👋 С возвращением, администратор!",
                    reply_markup=get_admin_menu_keyboard()
                )
            else:
                await message.answer(
                    f"👋 С возвращением!\n\nВыберите действие из меню:",
                    reply_markup=get_main_menu_keyboard()
                )
    finally:
        db.close()


@router.message(F.text == "ℹ️ Информация")
async def info_handler(message: Message):
    """Обработчик кнопки 'Информация'"""
    await message.answer(
        "ℹ️ <b>Информация о боте</b>\n\n"
        "Этот бот предназначен для размещения бартерных предложений в канале для блоггеров.\n\n"
        "<b>Как это работает:</b>\n"
        "1. Создайте пост через конструктор\n"
        "2. Выберите тип публикации:\n"
        "   • Бесплатная очередь - пост будет опубликован по порядку\n"
        "   • Приоритетная публикация (платно) - выберите точное время\n"
        "3. Ваш пост появится в канале\n"
        "4. Блоггеры оставят заявки в комментариях\n\n"
        "<b>Стоимость:</b>\n"
        "• Публикация в очереди: бесплатно\n"
        "• Приоритетная публикация: от 500₽\n\n"
        "По вопросам обращайтесь к администратору.",
        parse_mode="HTML"
    )
