from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from .models import User, Post, Payment, Setting, AdminLog


# === USER CRUD ===

def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(db: Session, telegram_id: int, username: str = None, full_name: str = None, contact: str = None, role: str = 'advertiser') -> User:
    """Создать нового пользователя"""
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        contact=contact,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, **kwargs) -> User:
    """Обновить пользователя"""
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


# === POST CRUD ===

def create_post(db: Session, user_id: int, **kwargs) -> Post:
    """Создать новый пост"""
    post = Post(user_id=user_id, **kwargs)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_post(db: Session, post_id: int) -> Optional[Post]:
    """Получить пост по ID"""
    return db.query(Post).filter(Post.id == post_id).first()


def get_user_posts(db: Session, user_id: int, status: Optional[str] = None) -> List[Post]:
    """Получить посты пользователя, опционально фильтруя по статусу"""
    query = db.query(Post).filter(Post.user_id == user_id)
    if status:
        query = query.filter(Post.status == status)
    return query.order_by(desc(Post.created_at)).all()


def get_posts_in_queue(db: Session) -> List[Post]:
    """Получить посты в очереди"""
    return db.query(Post).filter(Post.status == 'queue').order_by(asc(Post.queue_position)).all()


def get_scheduled_posts(db: Session) -> List[Post]:
    """Получить запланированные посты"""
    return db.query(Post).filter(Post.status == 'scheduled').order_by(asc(Post.scheduled_time)).all()


def update_post(db: Session, post: Post, **kwargs) -> Post:
    """Обновить пост"""
    for key, value in kwargs.items():
        if hasattr(post, key):
            setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post):
    """Удалить пост"""
    db.delete(post)
    db.commit()


def get_next_queue_position(db: Session) -> int:
    """Получить следующую позицию в очереди"""
    last_post = db.query(Post).filter(Post.status == 'queue').order_by(desc(Post.queue_position)).first()
    return (last_post.queue_position + 1) if last_post and last_post.queue_position else 1


def recalculate_queue_positions(db: Session):
    """Пересчитать позиции в очереди"""
    posts = db.query(Post).filter(Post.status == 'queue').order_by(asc(Post.queue_position)).all()
    for idx, post in enumerate(posts, start=1):
        post.queue_position = idx
    db.commit()


# === PAYMENT CRUD ===

def create_payment(db: Session, user_id: int, post_id: Optional[int], amount: float, **kwargs) -> Payment:
    """Создать новый платеж"""
    payment = Payment(
        user_id=user_id,
        post_id=post_id,
        amount=amount,
        **kwargs
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    """Получить платеж по ID"""
    return db.query(Payment).filter(Payment.id == payment_id).first()


def get_payment_by_payment_id(db: Session, payment_id: str) -> Optional[Payment]:
    """Получить платеж по ID из платежной системы"""
    return db.query(Payment).filter(Payment.payment_id == payment_id).first()


def update_payment(db: Session, payment: Payment, **kwargs) -> Payment:
    """Обновить платеж"""
    for key, value in kwargs.items():
        if hasattr(payment, key):
            setattr(payment, key, value)
    db.commit()
    db.refresh(payment)
    return payment


# === SETTING CRUD ===

def get_setting(db: Session, key: str) -> Optional[Setting]:
    """Получить настройку по ключу"""
    return db.query(Setting).filter(Setting.key == key).first()


def get_setting_value(db: Session, key: str, default: str = None) -> Optional[str]:
    """Получить значение настройки по ключу"""
    setting = get_setting(db, key)
    return setting.value if setting else default


def update_setting(db: Session, key: str, value: str) -> Setting:
    """Обновить настройку"""
    setting = get_setting(db, key)
    if setting:
        setting.value = value
        db.commit()
        db.refresh(setting)
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


# === ADMIN LOG CRUD ===

def create_admin_log(db: Session, admin_id: int, action: str, details: dict = None):
    """Создать запись в логе администратора"""
    log = AdminLog(
        admin_id=admin_id,
        action=action,
        details=details
    )
    db.add(log)
    db.commit()
