# -*- coding: utf-8 -*-
"""
Конфигурация бота для мастера маникюра
"""
import os

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8753248131:AAFDYcjwow3WP63yJFiNxQedfLJFr16BYMU")

# ID администратора (только он имеет доступ к админ-панели)
ADMIN_ID = int(os.getenv("ADMIN_ID", "1408233953"))

# ID канала для публикации расписания (без @)
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003720380952")

# Ссылка на канал для проверки подписки
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/nailsartemtest")

# Имя пользователя канала (без @) для ссылки подписки
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "nailsartemtest")

# Путь к базе данных SQLite
DATABASE_PATH = os.getenv("DATABASE_PATH", "manicure_bot.db")

# Время работы по умолчанию (слоты в минутах)
DEFAULT_SLOT_DURATION = 60  # 1 час

# Начало и конец рабочего дня по умолчанию
DEFAULT_WORK_START = "09:00"
DEFAULT_WORK_END = "20:00"
