#!/bin/bash

echo "🧹 Очистка и пересборка Docker окружения..."
echo ""

# Остановка и удаление всех контейнеров проекта
echo "1️⃣ Остановка контейнеров..."
docker-compose down -v 2>/dev/null || true

# Удаление старых контейнеров
echo "2️⃣ Удаление старых контейнеров..."
docker rm -f barter_bot barter_bot_celery barter_bot_celery_beat 2>/dev/null || true

# Удаление образов проекта
echo "3️⃣ Удаление старых образов..."
docker rmi barter_marketplace_bot barter_marketplace_celery_worker barter_marketplace_celery_beat 2>/dev/null || true
docker images | grep barter | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true

# Очистка неиспользуемых образов
echo "4️⃣ Очистка неиспользуемых образов..."
docker image prune -f

# Пересборка образов
echo "5️⃣ Пересборка образов..."
docker-compose build --no-cache

# Запуск контейнеров
echo "6️⃣ Запуск контейнеров..."
docker-compose up -d

echo ""
echo "✅ Готово!"
echo ""
echo "📊 Проверка статуса:"
docker-compose ps

echo ""
echo "📋 Логи бота:"
docker-compose logs --tail=20 barter_bot

echo ""
echo "📋 Логи Celery Worker:"
docker-compose logs --tail=20 barter_bot_celery

echo ""
echo "📋 Логи Celery Beat:"
docker-compose logs --tail=20 barter_bot_celery_beat
