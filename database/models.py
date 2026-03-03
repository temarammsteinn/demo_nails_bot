# -*- coding: utf-8 -*-
"""
SQL-схема и константы для базы данных
"""

# Таблица рабочих дней (дни, которые мастер работает)
CREATE_WORKING_DAYS = """
CREATE TABLE IF NOT EXISTS working_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    is_closed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Таблица временных слотов
CREATE_SLOTS = """
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    is_available INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, time),
    FOREIGN KEY (date) REFERENCES working_days(date)
);
"""

# Таблица записей (бронирований)
CREATE_BOOKINGS = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    client_name TEXT NOT NULL,
    client_phone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, time),
    FOREIGN KEY (date, time) REFERENCES slots(date, time)
);
"""

# Таблица задач напоминаний (для восстановления после перезапуска)
CREATE_REMINDERS = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    reminder_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);
"""

# Индексы для оптимизации
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_working_days_date ON working_days(date);",
    "CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date);",
    "CREATE INDEX IF NOT EXISTS idx_slots_available ON slots(date, time) WHERE is_available=1;",
    "CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time);",
]
