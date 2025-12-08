from typing import Optional, Tuple
from Levenshtein import ratio
import imagehash
from PIL import Image
from io import BytesIO


def check_text_similarity(text1: str, text2: str) -> float:
    """
    Проверка схожести текста с использованием Levenshtein distance

    Args:
        text1: Первый текст
        text2: Второй текст

    Returns:
        Процент схожести (0-100)
    """
    if not text1 or not text2:
        return 0.0

    similarity = ratio(text1.lower(), text2.lower())
    return similarity * 100


def check_image_similarity(image1_bytes: bytes, image2_bytes: bytes) -> float:
    """
    Проверка схожести изображений с использованием perceptual hash

    Args:
        image1_bytes: Байты первого изображения
        image2_bytes: Байты второго изображения

    Returns:
        Процент схожести (0-100)
    """
    try:
        img1 = Image.open(BytesIO(image1_bytes))
        img2 = Image.open(BytesIO(image2_bytes))

        hash1 = imagehash.average_hash(img1)
        hash2 = imagehash.average_hash(img2)

        # Hamming distance (чем меньше - тем больше схожесть)
        distance = hash1 - hash2

        # Преобразуем в процент схожести (максимальная дистанция = 64 для average_hash)
        similarity = (1 - (distance / 64)) * 100
        return max(0, similarity)
    except Exception as e:
        print(f"Ошибка при проверке схожести изображений: {e}")
        return 0.0


def check_duplicate(post_data: dict, existing_posts: list, threshold: float = 80.0) -> Tuple[bool, Optional[dict], float]:
    """
    Проверка на дубликаты постов

    Args:
        post_data: Данные нового поста
        existing_posts: Список существующих постов
        threshold: Порог схожести для определения дубликата (%)

    Returns:
        Tuple (is_duplicate, similar_post, similarity_score)
    """
    max_similarity = 0.0
    most_similar_post = None

    for existing_post in existing_posts:
        similarities = []

        # Проверка схожести названия
        if post_data.get('product_name') and existing_post.get('product_name'):
            name_similarity = check_text_similarity(
                post_data['product_name'],
                existing_post['product_name']
            )
            similarities.append(name_similarity)

        # Проверка схожести маркетплейса
        if post_data.get('marketplace') and existing_post.get('marketplace'):
            if post_data['marketplace'] == existing_post['marketplace']:
                similarities.append(100.0)
            else:
                similarities.append(0.0)

        # Проверка схожести тематики
        if post_data.get('blog_theme') and existing_post.get('blog_theme'):
            theme_similarity = check_text_similarity(
                post_data['blog_theme'],
                existing_post['blog_theme']
            )
            similarities.append(theme_similarity)

        # Средняя схожесть
        if similarities:
            avg_similarity = sum(similarities) / len(similarities)

            if avg_similarity > max_similarity:
                max_similarity = avg_similarity
                most_similar_post = existing_post

    is_duplicate = max_similarity >= threshold
    return is_duplicate, most_similar_post, max_similarity
