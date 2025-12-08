from celery import Celery
from bot.config import config

# Создание приложения Celery
celery_app = Celery(
    'barter_bot',
    broker=config.get_redis_url(),
    backend=config.get_redis_url(),
    include=['bot.tasks.publisher']
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    # Запуск проверки каждую минуту
    beat_schedule={
        'check-and-publish-every-minute': {
            'task': 'bot.tasks.publisher.check_and_publish',
            'schedule': 60.0,  # каждые 60 секунд
        },
    },
)
