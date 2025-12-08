import uuid
from yookassa import Configuration, Payment
from bot.config import config


def init_yookassa():
    """Инициализация ЮКасса"""
    Configuration.account_id = config.YOOKASSA_SHOP_ID
    Configuration.secret_key = config.YOOKASSA_SECRET_KEY


def create_yookassa_payment(amount: float, description: str, return_url: str = None) -> dict:
    """
    Создание платежа через ЮКасса

    Args:
        amount: Сумма платежа
        description: Описание платежа
        return_url: URL для возврата после оплаты

    Returns:
        Словарь с информацией о платеже
    """
    init_yookassa()

    idempotence_key = str(uuid.uuid4())

    payment_data = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url or "https://t.me/your_bot"
        },
        "capture": True,
        "description": description
    }

    try:
        payment = Payment.create(payment_data, idempotence_key)
        return {
            'id': payment.id,
            'status': payment.status,
            'amount': float(payment.amount.value),
            'currency': payment.amount.currency,
            'confirmation_url': payment.confirmation.confirmation_url,
            'paid': payment.paid,
        }
    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")
        return None


def check_payment_status(payment_id: str) -> dict:
    """
    Проверка статуса платежа

    Args:
        payment_id: ID платежа в ЮКасса

    Returns:
        Словарь с информацией о статусе платежа
    """
    init_yookassa()

    try:
        payment = Payment.find_one(payment_id)
        return {
            'id': payment.id,
            'status': payment.status,
            'paid': payment.paid,
            'amount': float(payment.amount.value),
            'currency': payment.amount.currency,
        }
    except Exception as e:
        print(f"Ошибка при проверке статуса платежа: {e}")
        return None
