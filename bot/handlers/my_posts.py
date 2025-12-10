from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session

from bot.database import get_db
from bot.database.crud import get_user_by_telegram_id
from bot.database.models import Post
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


# ===== МОИ ПУБЛИКАЦИИ =====

@router.message(F.text == "📋 Мои публикации")
async def my_publications_handler(message: Message):
    """Просмотр публикаций пользователя"""
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("❌ Ошибка: пользователь не найден. Отправьте /start для регистрации.")
            return

        # Получаем все посты пользователя кроме черновиков
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.status.in_(['queue', 'scheduled', 'published'])
        ).order_by(Post.created_at.desc()).all()

        if not posts:
            text = (
                "📋 <b>Мои публикации</b>\n\n"
                "У вас пока нет публикаций.\n\n"
                "Создайте пост, чтобы он появился здесь!"
            )
            await message.answer(text, parse_mode="HTML")
            return

        # Группируем посты по статусу
        queue_posts = [p for p in posts if p.status == 'queue']
        scheduled_posts = [p for p in posts if p.status == 'scheduled']
        published_posts = [p for p in posts if p.status == 'published']

        text = "📋 <b>Мои публикации</b>\n\n"

        if queue_posts:
            text += f"🕐 <b>В очереди:</b> {len(queue_posts)} постов\n"

        if scheduled_posts:
            text += f"⚡ <b>Запланировано:</b> {len(scheduled_posts)} постов\n"

        if published_posts:
            text += f"✅ <b>Опубликовано:</b> {len(published_posts)} постов\n"

        text += "\nВыберите раздел:"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🕐 В очереди ({len(queue_posts)})", callback_data="my_posts_queue:1")] if queue_posts else [],
            [InlineKeyboardButton(text=f"⚡ Запланировано ({len(scheduled_posts)})", callback_data="my_posts_scheduled:1")] if scheduled_posts else [],
            [InlineKeyboardButton(text=f"✅ Опубликовано ({len(published_posts)})", callback_data="my_posts_published:1")] if published_posts else [],
        ])

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("my_posts_queue:"))
async def my_posts_queue_handler(callback: CallbackQuery):
    """Посты в очереди"""
    page = int(callback.data.split(':')[1])
    page_size = 5

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.status == 'queue'
        ).order_by(Post.queue_position).all()

        if not posts:
            await callback.answer("Нет постов в очереди", show_alert=True)
            return

        total_pages = (len(posts) - 1) // page_size + 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_posts = posts[start_idx:end_idx]

        posts_text = ""
        for post in page_posts:
            posts_text += (
                f"\n📝 <b>{post.product_name[:40]}</b>\n"
                f"   ID: {post.id}\n"
                f"   Позиция: №{post.queue_position}\n"
                f"   Создан: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

        text = (
            f"🕐 <b>Посты в очереди (стр. {page}/{total_pages})</b>\n\n"
            f"Всего: {len(posts)} постов\n"
            f"{posts_text}\n"
            "Нажмите на ID для просмотра деталей."
        )

        buttons = []
        for post in page_posts:
            buttons.append([InlineKeyboardButton(
                text=f"ID {post.id}: {post.product_name[:25]}...",
                callback_data=f"my_post_detail:{post.id}"
            )])

        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_posts_queue:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_posts_queue:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("my_posts_scheduled:"))
async def my_posts_scheduled_handler(callback: CallbackQuery):
    """Запланированные посты"""
    page = int(callback.data.split(':')[1])
    page_size = 5

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.status == 'scheduled'
        ).order_by(Post.scheduled_time).all()

        if not posts:
            await callback.answer("Нет запланированных постов", show_alert=True)
            return

        total_pages = (len(posts) - 1) // page_size + 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_posts = posts[start_idx:end_idx]

        posts_text = ""
        for post in page_posts:
            scheduled_time = post.scheduled_time.strftime('%d.%m.%Y %H:%M') if post.scheduled_time else 'Не указано'
            posts_text += (
                f"\n📝 <b>{post.product_name[:40]}</b>\n"
                f"   ID: {post.id}\n"
                f"   Запланировано: {scheduled_time}\n"
                f"   Создан: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

        text = (
            f"⚡ <b>Запланированные посты (стр. {page}/{total_pages})</b>\n\n"
            f"Всего: {len(posts)} постов\n"
            f"{posts_text}\n"
            "Нажмите на ID для просмотра деталей."
        )

        buttons = []
        for post in page_posts:
            buttons.append([InlineKeyboardButton(
                text=f"ID {post.id}: {post.product_name[:25]}...",
                callback_data=f"my_post_detail:{post.id}"
            )])

        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_posts_scheduled:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_posts_scheduled:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("my_posts_published:"))
async def my_posts_published_handler(callback: CallbackQuery):
    """Опубликованные посты"""
    page = int(callback.data.split(':')[1])
    page_size = 5

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.status == 'published'
        ).order_by(Post.published_at.desc()).all()

        if not posts:
            await callback.answer("Нет опубликованных постов", show_alert=True)
            return

        total_pages = (len(posts) - 1) // page_size + 1
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_posts = posts[start_idx:end_idx]

        posts_text = ""
        for post in page_posts:
            published_time = post.published_at.strftime('%d.%m.%Y %H:%M') if post.published_at else 'Не указано'
            posts_text += (
                f"\n📝 <b>{post.product_name[:40]}</b>\n"
                f"   ID: {post.id}\n"
                f"   Опубликовано: {published_time}\n"
                f"   Создан: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )

        text = (
            f"✅ <b>Опубликованные посты (стр. {page}/{total_pages})</b>\n\n"
            f"Всего: {len(posts)} постов\n"
            f"{posts_text}\n"
            "Нажмите на ID для просмотра деталей."
        )

        buttons = []
        for post in page_posts:
            buttons.append([InlineKeyboardButton(
                text=f"ID {post.id}: {post.product_name[:25]}...",
                callback_data=f"my_post_detail:{post.id}"
            )])

        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"my_posts_published:{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"my_posts_published:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("my_post_detail:"))
async def my_post_detail_handler(callback: CallbackQuery):
    """Детали поста пользователя"""
    post_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user.id
        ).first()

        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return

        status_emoji = {
            'queue': '🕐',
            'scheduled': '⚡',
            'published': '✅',
            'draft': '💾'
        }

        text = (
            f"{status_emoji.get(post.status, '📝')} <b>Пост #{post.id}</b>\n\n"
            f"<b>Товар:</b> {post.product_name}\n"
            f"<b>Статус:</b> {post.status}\n"
        )

        if post.queue_position:
            text += f"<b>Позиция в очереди:</b> №{post.queue_position}\n"

        if post.scheduled_time:
            text += f"<b>Запланировано:</b> {post.scheduled_time.strftime('%d.%m.%Y %H:%M')}\n"

        if post.published_at:
            text += f"<b>Опубликовано:</b> {post.published_at.strftime('%d.%m.%Y %H:%M')}\n"

        text += (
            f"\n<b>Доплата:</b> {post.has_payment or 'Нет'}\n"
            f"<b>Маркетплейс:</b> {post.marketplace}\n"
            f"<b>Тематика:</b> {post.blog_theme}\n"
            f"<b>Соцсети:</b> {', '.join(post.social_networks) if post.social_networks else 'Не указано'}\n"
            f"<b>Условия:</b> {post.conditions}\n\n"
            f"<b>Создан:</b> {post.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к списку", callback_data=f"my_posts_{post.status}:1")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


# ===== МОИ ЧЕРНОВИКИ =====

@router.message(F.text == "💾 Мои черновики")
async def my_drafts_handler(message: Message):
    """Просмотр черновиков пользователя"""
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("❌ Ошибка: пользователь не найден. Отправьте /start для регистрации.")
            return

        drafts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.status == 'draft'
        ).order_by(Post.created_at.desc()).all()

        if not drafts:
            text = (
                "💾 <b>Мои черновики</b>\n\n"
                "У вас нет сохраненных черновиков.\n\n"
                "Черновики создаются когда вы сохраняете незавершенный пост."
            )
            await message.answer(text, parse_mode="HTML")
            return

        text = f"💾 <b>Мои черновики</b>\n\nВсего черновиков: {len(drafts)}\n\n"

        for idx, draft in enumerate(drafts[:10], 1):
            text += (
                f"{idx}. <b>{draft.product_name[:30]}</b>\n"
                f"   ID: {draft.id}\n"
                f"   Создан: {draft.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            )

        if len(drafts) > 10:
            text += f"... и еще {len(drafts) - 10} черновиков\n\n"

        text += "Выберите черновик для просмотра:"

        buttons = []
        for draft in drafts[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"ID {draft.id}: {draft.product_name[:30]}...",
                callback_data=f"draft_detail:{draft.id}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("draft_detail:"))
async def draft_detail_handler(callback: CallbackQuery):
    """Детали черновика"""
    draft_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        draft = db.query(Post).filter(
            Post.id == draft_id,
            Post.user_id == user.id,
            Post.status == 'draft'
        ).first()

        if not draft:
            await callback.answer("Черновик не найден", show_alert=True)
            return

        text = (
            f"💾 <b>Черновик #{draft.id}</b>\n\n"
            f"<b>Товар:</b> {draft.product_name}\n"
            f"<b>Доплата:</b> {draft.has_payment or 'Нет'}\n"
            f"<b>Маркетплейс:</b> {draft.marketplace}\n"
            f"<b>Тематика:</b> {draft.blog_theme}\n"
            f"<b>Соцсети:</b> {', '.join(draft.social_networks) if draft.social_networks else 'Не указано'}\n"
            f"<b>Условия:</b> {draft.conditions}\n\n"
            f"<b>Создан:</b> {draft.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            "⚠️ Функционал завершения черновиков будет добавлен позже."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить черновик", callback_data=f"delete_draft:{draft.id}")],
            [InlineKeyboardButton(text="◀️ К черновикам", callback_data="back_to_drafts")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    finally:
        db.close()


@router.callback_query(F.data.startswith("delete_draft:"))
async def delete_draft_handler(callback: CallbackQuery):
    """Удаление черновика"""
    draft_id = int(callback.data.split(':')[1])

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)
        draft = db.query(Post).filter(
            Post.id == draft_id,
            Post.user_id == user.id,
            Post.status == 'draft'
        ).first()

        if not draft:
            await callback.answer("Черновик не найден", show_alert=True)
            return

        db.delete(draft)
        db.commit()

        await callback.answer("✅ Черновик удален", show_alert=True)
        await callback.message.edit_text(
            "✅ Черновик успешно удален.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К черновикам", callback_data="back_to_drafts")]
            ])
        )

    finally:
        db.close()


@router.callback_query(F.data == "back_to_drafts")
async def back_to_drafts_handler(callback: CallbackQuery):
    """Возврат к списку черновиков"""
    await callback.message.delete()
    # Имитация нажатия кнопки "Мои черновики"
    from aiogram.types import Message as Msg
    # Создаем фейковое сообщение для вызова обработчика
    fake_message = callback.message
    fake_message.text = "💾 Мои черновики"
    await my_drafts_handler(fake_message)
