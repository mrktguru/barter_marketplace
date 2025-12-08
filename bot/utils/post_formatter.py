def format_post_for_channel(post_data: dict) -> str:
    """
    Форматирование поста для публикации в канале

    Args:
        post_data: Словарь с данными поста

    Returns:
        Отформатированный текст поста
    """
    text_parts = []

    # Название товара
    if post_data.get('product_name'):
        text_parts.append(f"<b>{post_data['product_name']}</b>\n")

    # Доплата
    if post_data.get('has_payment'):
        payment_text = post_data['has_payment']
        if post_data.get('payment_amount'):
            payment_text = f"{payment_text} ({post_data['payment_amount']})"
        text_parts.append(f"Доплата:\n🔸 {payment_text}\n")

    # Маркетплейс
    if post_data.get('marketplace'):
        text_parts.append(f"Маркетплейс:\n🔸 {post_data['marketplace']}\n")

    # Ожидаемая дата публикации
    if post_data.get('expected_date'):
        text_parts.append(f"Ожидаемая дата публикации:\n🔸 {post_data['expected_date']}\n")

    # Тематика блога
    if post_data.get('blog_theme'):
        text_parts.append(f"Тематика блога:\n🔸 {post_data['blog_theme']}\n")

    # Требования к соцсетям
    if post_data.get('social_networks'):
        networks = ', '.join(post_data['social_networks'])
        text_parts.append(f"Требования к соцсетям:\n🔸 {networks}\n")

    # Формат рекламы
    if post_data.get('ad_formats'):
        text_parts.append("Формат рекламы:")
        for network, format_text in post_data['ad_formats'].items():
            text_parts.append(f"🔸 {network}: {format_text}")
        text_parts.append("")

    # Условия
    if post_data.get('conditions'):
        text_parts.append("Условия:")
        conditions = post_data['conditions']
        if isinstance(conditions, list):
            for condition in conditions:
                text_parts.append(f"🔻 {condition}")
        else:
            text_parts.append(f"🔻 {conditions}")
        text_parts.append("")

    # Для сотрудничества
    text_parts.append("Для сотрудничества:\nЗаявки в комментарии со скринами статистики")

    return "\n".join(text_parts)


def format_post_preview(post_data: dict) -> str:
    """
    Форматирование поста для предпросмотра пользователю

    Args:
        post_data: Словарь с данными поста

    Returns:
        Отформатированный текст предпросмотра
    """
    text = "👁 <b>Предпросмотр поста</b>\n\n"
    text += "──────────────────\n\n"
    text += format_post_for_channel(post_data)
    text += "\n\n──────────────────\n"
    return text
