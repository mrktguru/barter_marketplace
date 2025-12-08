from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean,
    DECIMAL, TIMESTAMP, Text, ForeignKey, ARRAY, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    full_name = Column(String(255))
    contact = Column(String(255))
    role = Column(String(50), default='advertiser', index=True)  # 'admin' или 'advertiser'
    balance = Column(DECIMAL(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relationships
    posts = relationship('Post', back_populates='user', cascade='all, delete-orphan')
    payments = relationship('Payment', back_populates='user', cascade='all, delete-orphan')
    admin_logs = relationship('AdminLog', back_populates='admin')

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(String(50), default='draft', index=True)  # 'draft', 'queue', 'scheduled', 'published', 'rejected'

    # Контент поста
    image_file_id = Column(String(255))
    product_name = Column(Text, nullable=False)
    has_payment = Column(String(50))  # 'Нет', 'Есть', 'Обсуждается'
    payment_amount = Column(String(100))
    marketplace = Column(String(100))
    expected_date = Column(Text)
    blog_theme = Column(Text)
    social_networks = Column(ARRAY(Text))  # массив выбранных соцсетей
    ad_formats = Column(JSON)  # {'instagram': 'Reels / 5000+', 'tiktok': 'Video / 2000+'}
    conditions = Column(Text)

    # Метаданные
    queue_position = Column(Integer, index=True)
    scheduled_time = Column(TIMESTAMP, index=True)  # для приоритетных постов
    published_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Платежная информация
    payment_type = Column(String(50))  # 'queue' или 'priority'
    payment_status = Column(String(50))  # 'pending', 'paid', 'failed'
    payment_amount_value = Column(DECIMAL(10, 2))

    # Ссылка на опубликованный пост
    channel_message_id = Column(Integer)
    channel_post_url = Column(Text)

    # Relationships
    user = relationship('User', back_populates='posts')
    payments = relationship('Payment', back_populates='post')

    def __repr__(self):
        return f"<Post(id={self.id}, product_name={self.product_name}, status={self.status})>"


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='SET NULL'), index=True)

    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default='RUB')

    payment_system = Column(String(50))  # 'yookassa', 'robokassa', etc.
    payment_id = Column(String(255), unique=True, index=True)  # ID из платежной системы
    payment_url = Column(Text)

    status = Column(String(50), default='pending', index=True)  # 'pending', 'succeeded', 'failed', 'cancelled'

    created_at = Column(TIMESTAMP, default=func.now())
    paid_at = Column(TIMESTAMP)

    # Relationships
    user = relationship('User', back_populates='payments')
    post = relationship('Post', back_populates='payments')

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status})>"


class Setting(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Setting(key={self.key}, value={self.value})>"


class AdminLog(Base):
    __tablename__ = 'admin_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey('users.id'), index=True)
    action = Column(String(255), nullable=False)
    details = Column(JSON)
    created_at = Column(TIMESTAMP, default=func.now(), index=True)

    # Relationships
    admin = relationship('User', back_populates='admin_logs')

    def __repr__(self):
        return f"<AdminLog(id={self.id}, action={self.action})>"
