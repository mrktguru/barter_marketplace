import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Setting

# Получение параметров подключения из переменных окружения
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'barter_bot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# Строка подключения к базе данных
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создание движка базы данных
engine = create_engine(DATABASE_URL, echo=False)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Получение сессии базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализация базы данных - создание таблиц и заполнение настроек
    """
    # Создание всех таблиц
    Base.metadata.create_all(bind=engine)

    # Заполнение настроек по умолчанию
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже настройки
        existing_settings = db.query(Setting).count()
        if existing_settings == 0:
            default_settings = [
                Setting(key='channel_id', value=None, description='ID канала для публикаций'),
                Setting(key='channel_username', value=None, description='Username канала'),
                Setting(key='posts_per_day', value='5', description='Количество постов в день из очереди'),
                Setting(key='schedule_times', value='10:00,13:00,16:00,19:00,22:00', description='Время публикаций (через запятую)'),
                Setting(key='queue_price', value='0', description='Цена публикации в очереди (₽)'),
                Setting(key='priority_price', value='500', description='Цена приоритетной публикации (₽)'),
                Setting(key='max_queue_days', value='30', description='Максимум дней ожидания в очереди'),
                Setting(key='duplicate_threshold', value='80', description='Порог схожести для определения дубликата (%)'),
            ]
            db.add_all(default_settings)
            db.commit()
            print("✅ Настройки по умолчанию добавлены в базу данных")
    except Exception as e:
        print(f"❌ Ошибка при инициализации настроек: {e}")
        db.rollback()
    finally:
        db.close()
