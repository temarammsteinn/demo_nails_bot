# -*- coding: utf-8 -*-
"""
Планировщик напоминаний за 24 часа до записи
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from database import get_db

# Глобальный планировщик
_scheduler: AsyncIOScheduler = None
_bot = None  # Ссылка на бот для отправки сообщений


def init_scheduler(bot):
    """Инициализация планировщика и восстановление задач из БД"""
    global _scheduler, _bot
    _bot = bot
    _scheduler = AsyncIOScheduler()
    _scheduler.start()

    # Восстановление напоминаний из БД
    db = get_db()
    reminders = db.get_pending_reminders()
    for r in reminders:
        try:
            reminder_time = datetime.fromisoformat(r["reminder_time"])
            if reminder_time > datetime.now():
                _scheduler.add_job(
                    send_reminder,
                    DateTrigger(run_date=reminder_time),
                    id=f"reminder_{r['booking_id']}",
                    args=[r["user_id"], r["time"]],
                    replace_existing=True,
                )
        except Exception as e:
            print(f"Ошибка восстановления напоминания {r.get('booking_id')}: {e}")


def schedule_reminder(booking_id: int, user_id: int, date: str, time: str) -> bool:
    """
    Запланировать напоминание за 24 часа до записи.
    Возвращает True если напоминание создано, False если запись менее чем за 24ч.
    """
    global _scheduler
    if not _scheduler:
        return False

    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        reminder_time = dt - timedelta(hours=24)

        if reminder_time <= datetime.now():
            return False  # Меньше 24 часов - не создаём

        # Сохраняем в БД для восстановления при перезапуске
        db = get_db()
        db.add_reminder(booking_id, user_id, date, time, reminder_time)

        _scheduler.add_job(
            send_reminder,
            DateTrigger(run_date=reminder_time),
            id=f"reminder_{booking_id}",
            args=[user_id, time],
            replace_existing=True,
        )
        return True
    except Exception as e:
        print(f"Ошибка планирования напоминания: {e}")
        return False


def cancel_reminder(booking_id: int):
    """Удалить задачу напоминания при отмене записи"""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.remove_job(f"reminder_{booking_id}")
        except Exception:
            pass

    db = get_db()
    db.remove_reminder(booking_id)


async def send_reminder(user_id: int, time: str):
    """Отправить напоминание пользователю"""
    global _bot
    if _bot:
        text = (
            f"⏰ <b>Напоминание</b>\n\n"
            f"Напоминаем, что вы записаны на наращивание ресниц завтра в <b>{time}</b>.\n"
            f"Ждём вас 💕"
        )
        try:
            await _bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"Ошибка отправки напоминания: {e}")


def shutdown_scheduler():
    """Остановка планировщика"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
