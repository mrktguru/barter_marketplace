"""
Утилиты для отправки сообщений в Telegram из синхронных контекстов (Celery)
"""

import asyncio
import requests
from typing import Optional
from bot.config import config


def send_message_sync(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """
    Синхронная отправка текстового сообщения в Telegram

    Args:
        chat_id: ID чата или канала
        text: Текст сообщения
        parse_mode: Режим форматирования (HTML, Markdown)

    Returns:
        True если успешно, False если ошибка
    """
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200

    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        return False


def send_photo_sync(chat_id: str, photo: str, caption: Optional[str] = None, parse_mode: str = "HTML") -> bool:
    """
    Синхронная отправка фото в Telegram

    Args:
        chat_id: ID чата или канала
        photo: file_id фотографии
        caption: Подпись к фото
        parse_mode: Режим форматирования (HTML, Markdown)

    Returns:
        True если успешно, False если ошибка
    """
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "photo": photo,
            "parse_mode": parse_mode
        }

        if caption:
            data["caption"] = caption

        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200

    except Exception as e:
        print(f"Ошибка при отправке фото: {e}")
        return False


async def send_message_async(bot, chat_id: str, text: str, parse_mode: str = "HTML"):
    """
    Асинхронная отправка текстового сообщения

    Args:
        bot: Экземпляр бота
        chat_id: ID чата или канала
        text: Текст сообщения
        parse_mode: Режим форматирования
    """
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        return False


async def send_photo_async(bot, chat_id: str, photo: str, caption: Optional[str] = None, parse_mode: str = "HTML"):
    """
    Асинхронная отправка фото

    Args:
        bot: Экземпляр бота
        chat_id: ID чата или канала
        photo: file_id фотографии
        caption: Подпись к фото
        parse_mode: Режим форматирования
    """
    try:
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode=parse_mode)
        return True
    except Exception as e:
        print(f"Ошибка при отправке фото: {e}")
        return False
