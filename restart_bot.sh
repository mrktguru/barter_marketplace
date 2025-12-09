#!/bin/bash

# Скрипт для перезапуска бота

echo "🔄 Перезапуск бота..."

# Проверка наличия docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    echo "❌ Ошибка: docker или docker-compose не найден"
    exit 1
fi

# Остановка бота
echo "🛑 Остановка контейнера бота..."
$DOCKER_CMD stop barter_bot

# Пересборка образа (на случай изменений в коде)
echo "🔨 Пересборка образа..."
$DOCKER_CMD build bot

# Запуск бота
echo "▶️ Запуск бота..."
$DOCKER_CMD up -d barter_bot

# Проверка логов
echo "📋 Логи бота:"
$DOCKER_CMD logs --tail=20 barter_bot

echo ""
echo "✅ Готово! Бот перезапущен."
echo "📊 Для просмотра логов используйте: $DOCKER_CMD logs -f barter_bot"
