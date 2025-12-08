from aiogram.fsm.state import State, StatesGroup


class PostCreation(StatesGroup):
    """Состояния для создания поста"""
    # Шаги создания поста
    image = State()  # Шаг 1: Загрузка изображения
    product_name = State()  # Шаг 2: Название товара
    payment = State()  # Шаг 3: Доплата
    payment_amount = State()  # Шаг 3.1: Сумма доплаты (если есть)
    marketplace = State()  # Шаг 4: Маркетплейс
    marketplace_custom = State()  # Шаг 4.1: Другой маркетплейс (если "Другой")
    expected_date = State()  # Шаг 5: Ожидаемая дата публикации
    expected_date_custom = State()  # Шаг 5.1: Ввод конкретной даты
    blog_theme = State()  # Шаг 6: Тематика блога
    blog_theme_custom = State()  # Шаг 6.1: Своя тематика
    social_networks = State()  # Шаг 7: Социальные сети
    ad_formats = State()  # Шаг 7.1: Формат рекламы для каждой соцсети
    conditions = State()  # Шаг 8: Условия сотрудничества
    conditions_custom = State()  # Шаг 8.1: Свои условия
    preview = State()  # Шаг 9: Предпросмотр

    # Публикация
    priority_date = State()  # Выбор даты для приоритетной публикации
    priority_time = State()  # Выбор времени для приоритетной публикации


class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    # Настройка канала
    set_channel = State()

    # Настройка расписания
    set_posts_count = State()
    set_schedule_times = State()

    # Настройка тарифов
    set_queue_price = State()
    set_priority_price = State()
