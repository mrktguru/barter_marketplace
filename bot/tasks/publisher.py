from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session

from bot.database import SessionLocal
from bot.database.crud import get_posts_in_queue, get_scheduled_posts, update_post, recalculate_queue_positions, get_setting_value
from bot.utils.post_formatter import format_post_for_channel


@shared_task(name='bot.tasks.publisher.check_and_publish')
def check_and_publish():
    """
    Задача Celery для проверки и публикации постов
    Выполняется каждую минуту
    """
    db = SessionLocal()
    try:
        current_time = datetime.now()
        current_time_str = current_time.strftime('%H:%M')

        # 1. Проверка приоритетных постов
        scheduled_posts = get_scheduled_posts(db)
        for post in scheduled_posts:
            if post.scheduled_time and post.scheduled_time <= current_time:
                # Публикация приоритетного поста
                publish_post_to_channel(db, post)

        # 2. Проверка расписания для постов из очереди
        schedule_times = get_setting_value(db, 'schedule_times', '10:00,13:00,16:00,19:00,22:00')
        schedule_list = [time.strip() for time in schedule_times.split(',')]

        if current_time_str in schedule_list:
            # Время для публикации из очереди
            queue_posts = get_posts_in_queue(db)
            if queue_posts:
                first_post = queue_posts[0]
                publish_post_to_channel(db, first_post)
                recalculate_queue_positions(db)

        return f"Проверка завершена в {current_time_str}"
    except Exception as e:
        print(f"Ошибка при проверке и публикации: {e}")
        return f"Ошибка: {e}"
    finally:
        db.close()


def publish_post_to_channel(db: Session, post):
    """
    Публикация поста в канал

    Args:
        db: Сессия базы данных
        post: Объект поста
    """
    try:
        # Получение ID канала из настроек
        channel_id = get_setting_value(db, 'channel_id')

        if not channel_id:
            print("Ошибка: ID канала не настроен")
            return

        # Форматирование текста поста
        post_data = {
            'product_name': post.product_name,
            'has_payment': post.has_payment,
            'payment_amount': post.payment_amount,
            'marketplace': post.marketplace,
            'expected_date': post.expected_date,
            'blog_theme': post.blog_theme,
            'social_networks': post.social_networks,
            'ad_formats': post.ad_formats,
            'conditions': post.conditions,
        }

        text = format_post_for_channel(post_data)

        # Отправка в Telegram канал
        from bot.utils.telegram_sender import send_photo_sync, send_message_sync

        success = False
        if post.image_file_id:
            success = send_photo_sync(
                chat_id=channel_id,
                photo=post.image_file_id,
                caption=text,
                parse_mode="HTML"
            )
        else:
            success = send_message_sync(
                chat_id=channel_id,
                text=text,
                parse_mode="HTML"
            )

        if success:
            # Обновление статуса поста
            update_post(
                db=db,
                post=post,
                status='published',
                published_at=datetime.now()
            )

            print(f"✅ Пост {post.id} опубликован в канал {channel_id}")

            # TODO: Отправка уведомления пользователю о публикации
        else:
            print(f"❌ Не удалось опубликовать пост {post.id} в канал")

    except Exception as e:
        print(f"❌ Ошибка при публикации поста {post.id}: {e}")
