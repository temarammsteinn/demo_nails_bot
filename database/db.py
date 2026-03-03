# -*- coding: utf-8 -*-
"""
Операции с базой данных SQLite
"""
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

import config
from .models import (
    CREATE_WORKING_DAYS,
    CREATE_SLOTS,
    CREATE_BOOKINGS,
    CREATE_REMINDERS,
    CREATE_INDEXES,
)


def get_db_path():
    """Получить путь к БД"""
    return config.DATABASE_PATH


def run_sync(coro):
    """Выполнить синхронную функцию в executor"""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, coro)


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_db_path()

    def _get_connection(self):
        """Создать подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Возвращать словари
        return conn

    def init_db(self):
        """Инициализация БД: создание таблиц"""
        conn = self._get_connection()
        try:
            conn.executescript(
                CREATE_WORKING_DAYS
                + CREATE_SLOTS
                + CREATE_BOOKINGS
                + CREATE_REMINDERS
            )
            for idx_sql in CREATE_INDEXES:
                conn.execute(idx_sql)
            conn.commit()
        finally:
            conn.close()

    def add_working_day(self, date: str) -> bool:
        """Добавить рабочий день"""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO working_days (date) VALUES (?)", (date,)
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def add_working_days_range(self, start_date: str, end_date: str):
        """Добавить диапазон рабочих дней"""
        conn = self._get_connection()
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                conn.execute(
                    "INSERT OR IGNORE INTO working_days (date) VALUES (?)",
                    (date_str,),
                )
                current += timedelta(days=1)
            conn.commit()
        finally:
            conn.close()

    def close_day(self, date: str):
        """Полностью закрыть день"""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE working_days SET is_closed = 1 WHERE date = ?", (date,)
            )
            conn.execute("UPDATE slots SET is_available = 0 WHERE date = ?", (date,))
            conn.commit()
        finally:
            conn.close()

    def open_day(self, date: str):
        """Открыть день обратно"""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE working_days SET is_closed = 0 WHERE date = ?", (date,)
            )
            conn.commit()
        finally:
            conn.close()

    def add_slot(self, date: str, time: str) -> bool:
        """Добавить временной слот"""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO slots (date, time) VALUES (?, ?)",
                (date, time),
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def remove_slot(self, date: str, time: str):
        """Удалить временной слот"""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM slots WHERE date = ? AND time = ?", (date, time))
            conn.commit()
        finally:
            conn.close()

    def get_available_dates(self, months_ahead: int = 1) -> list:
        """Получить доступные даты на N месяцев вперед"""
        conn = self._get_connection()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=months_ahead * 31)).strftime(
                "%Y-%m-%d"
            )
            cursor = conn.execute(
                """
                SELECT wd.date FROM working_days wd
                WHERE wd.date >= ? AND wd.date <= ?
                AND wd.is_closed = 0
                AND EXISTS (
                    SELECT 1 FROM slots s
                    WHERE s.date = wd.date AND s.is_available = 1
                )
                ORDER BY wd.date
                """,
                (today, end_date),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_available_slots(self, date: str) -> list:
        """Получить доступные слоты на дату"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT time FROM slots
                WHERE date = ? AND is_available = 1
                ORDER BY time
                """,
                (date,),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_slots_for_admin(self, date: str) -> list:
        """Получить все слоты на дату для админа"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT s.time, s.is_available, b.client_name, b.client_phone, b.user_id
                FROM slots s
                LEFT JOIN bookings b ON s.date = b.date AND s.time = b.time
                WHERE s.date = ?
                ORDER BY s.time
                """,
                (date,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_working_days_with_slots(self, months_ahead: int = 1) -> list:
        """Получить рабочие дни со слотами"""
        return self.get_available_dates(months_ahead)

    def has_user_booking(self, user_id: int) -> Optional[dict]:
        """Проверить, есть ли у пользователя активная запись"""
        conn = self._get_connection()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            cursor = conn.execute(
                """
                SELECT id, date, time, client_name, client_phone
                FROM bookings
                WHERE user_id = ? AND date >= ?
                """,
                (user_id, today),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_booking(
        self, user_id: int, date: str, time: str, name: str, phone: str
    ) -> Optional[int]:
        """Создать бронирование. Возвращает ID записи или None"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO bookings (user_id, date, time, client_name, client_phone)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, date, time, name, phone),
            )
            booking_id = cursor.lastrowid
            conn.execute(
                "UPDATE slots SET is_available = 0 WHERE date = ? AND time = ?",
                (date, time),
            )
            conn.commit()
            return booking_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def cancel_booking(self, booking_id: int = None, user_id: int = None) -> Optional[dict]:
        """
        Отменить бронирование.
        Можно по booking_id или по user_id (отменит первую найденную запись пользователя).
        Возвращает данные отменённой записи.
        """
        conn = self._get_connection()
        try:
            if booking_id:
                cursor = conn.execute(
                    "SELECT id, user_id, date, time FROM bookings WHERE id = ?",
                    (booking_id,),
                )
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                cursor = conn.execute(
                    "SELECT id, user_id, date, time FROM bookings WHERE user_id = ? AND date >= ?",
                    (user_id, today),
                )
            row = cursor.fetchone()
            if not row:
                return None

            booking = dict(row)
            conn.execute("DELETE FROM bookings WHERE id = ?", (booking["id"],))
            conn.execute(
                "UPDATE slots SET is_available = 1 WHERE date = ? AND time = ?",
                (booking["date"], booking["time"]),
            )
            conn.execute("DELETE FROM reminders WHERE booking_id = ?", (booking["id"],))
            conn.commit()
            return booking
        finally:
            conn.close()

    def get_booking_by_id(self, booking_id: int) -> Optional[dict]:
        """Получить запись по ID"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM bookings WHERE id = ?", (booking_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_booking_details(self, user_id: int) -> Optional[dict]:
        """Получить детали записи пользователя"""
        return self.has_user_booking(user_id)

    # === Работа с напоминаниями ===

    def add_reminder(
        self, booking_id: int, user_id: int, date: str, time: str, reminder_time: datetime
    ):
        """Добавить задачу напоминания"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO reminders (booking_id, user_id, date, time, reminder_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (booking_id, user_id, date, time, reminder_time.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_reminder(self, booking_id: int):
        """Удалить задачу напоминания"""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM reminders WHERE booking_id = ?", (booking_id,))
            conn.commit()
        finally:
            conn.close()

    def get_pending_reminders(self) -> list:
        """Получить все pending напоминания (для восстановления при старте)"""
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """
                SELECT r.id, r.booking_id, r.user_id, r.date, r.time, r.reminder_time
                FROM reminders r
                JOIN bookings b ON r.booking_id = b.id
                WHERE r.reminder_time > ?
                ORDER BY r.reminder_time
                """,
                (now,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_slots_for_date(self, date: str) -> list:
        """Получить все слоты на дату (для админа - генерация расписания)"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT time FROM slots WHERE date = ? ORDER BY time", (date,)
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def generate_slots_for_day(
        self, date: str, start_time: str = "09:00", end_time: str = "20:00", duration: int = 60
    ):
        """Сгенерировать слоты для дня"""
        conn = self._get_connection()
        try:
            start = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
            current = start
            while current < end:
                time_str = current.strftime("%H:%M")
                conn.execute(
                    "INSERT OR IGNORE INTO slots (date, time) VALUES (?, ?)",
                    (date, time_str),
                )
                current += timedelta(minutes=duration)
            conn.commit()
        finally:
            conn.close()


# Глобальный экземпляр БД
_db: Optional[Database] = None


def get_db() -> Database:
    """Получить экземпляр БД"""
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_db():
    """Инициализировать БД"""
    db = get_db()
    db.init_db()
