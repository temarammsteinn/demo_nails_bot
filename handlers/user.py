# -*- coding: utf-8 -*-
"""
Обработчики пользователя: запись, отмена
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_db
from keyboards.inline import (
    get_main_menu_keyboard,
    get_calendar_keyboard,
    get_time_slots_keyboard,
    get_confirm_keyboard,
    get_subscribe_keyboard,
)
from handlers.states import BookingStates
from utils.channel_check import check_channel_subscription
from utils.scheduler import schedule_reminder, cancel_reminder

import config

router = Router()

# Хранилище выбранной даты/времени (между callback и message)
_user_booking_data: dict = {}


def _get_booking_data(user_id: int) -> dict:
    if user_id not in _user_booking_data:
        _user_booking_data[user_id] = {}
    return _user_booking_data[user_id]


# === Команда /start ===
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие и главное меню"""
    await state.clear()
    text = (
        "<b>💅 Добро пожаловать!</b>\n\n"
        "Я бот мастера маникюра. Выберите действие:"
    )
    user_id = message.from_user.id if message.from_user else None
    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(user_id),
    )


# === Назад в главное меню ===
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    text = "Выберите действие:"
    user_id = callback.from_user.id if callback.from_user else None
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(user_id),
    )
    await callback.answer()


# === Начало записи (проверка подписки) ===
@router.callback_query(F.data == "booking_start")
async def booking_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса записи - проверка подписки"""
    await state.clear()
    user_id = callback.from_user.id

    # Проверка подписки на канал
    from aiogram import Bot
    bot = callback.bot
    is_subscribed = await check_channel_subscription(bot, user_id)

    if not is_subscribed:
        text = (
            "<b>📢 Требуется подписка</b>\n\n"
            "Для записи необходимо подписаться на наш канал.\n"
            "После подписки нажмите «Проверить подписку»."
        )
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard(),
        )
        await callback.answer()
        return

    # Проверка: нет ли уже активной записи
    db = get_db()
    existing = db.has_user_booking(user_id)
    if existing:
        text = (
            f"<b>⚠️ У вас уже есть активная запись</b>\n\n"
            f"📅 Дата: <b>{existing['date']}</b>\n"
            f"🕐 Время: <b>{existing['time']}</b>\n\n"
            "Сначала отмените текущую запись, чтобы записаться на другую дату."
        )
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(user_id),
        )
        await callback.answer()
        return

    # Показываем календарь
    dates = db.get_available_dates(months_ahead=1)
    if not dates:
        text = "😔 К сожалению, на ближайший месяц нет свободных слотов."
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(user_id),
        )
        await callback.answer()
        return

    await state.set_state(BookingStates.selecting_date)
    text = "<b>📅 Выберите дату записи:</b>"
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_calendar_keyboard(dates, page=0),
    )
    await callback.answer()


# === Проверка подписки ===
@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    """Проверка подписки и переход к записи"""
    user_id = callback.from_user.id
    is_subscribed = await check_channel_subscription(callback.bot, user_id)

    if is_subscribed:
        await callback.answer("✅ Спасибо за подписку! Теперь вы можете записаться.")
        db = get_db()
        existing = db.has_user_booking(user_id)
        if existing:
            text = (
                f"<b>⚠️ У вас уже есть активная запись</b>\n\n"
                f"📅 Дата: <b>{existing['date']}</b>\n🕐 Время: <b>{existing['time']}</b>\n\n"
                "Сначала отмените текущую запись."
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(user_id))
            return
        dates = db.get_available_dates(months_ahead=1)
        if not dates:
            await callback.message.edit_text("😔 Нет свободных слотов.", reply_markup=get_main_menu_keyboard(user_id))
            return
        await state.set_state(BookingStates.selecting_date)
        await callback.message.edit_text(
            "<b>📅 Выберите дату записи:</b>",
            parse_mode="HTML",
            reply_markup=get_calendar_keyboard(dates),
        )
    else:
        await callback.answer("❌ Подписка не обнаружена. Пожалуйста, подпишитесь на канал.", show_alert=True)


# === Пагинация календаря ===
@router.callback_query(F.data.startswith("calendar_page_"), BookingStates.selecting_date)
async def calendar_page(callback: CallbackQuery, state: FSMContext):
    """Переключение страницы календаря"""
    page = int(callback.data.split("_")[-1])
    db = get_db()
    dates = db.get_available_dates(months_ahead=1)
    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(dates, page=page),
    )
    await callback.answer()


# === Выбор даты ===
@router.callback_query(F.data.startswith("date_"), BookingStates.selecting_date)
async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты -> показ слотов"""
    date = callback.data.replace("date_", "")
    db = get_db()
    slots = db.get_available_slots(date)
    if not slots:
        await callback.answer("Нет свободных слотов на эту дату", show_alert=True)
        return

    await state.update_data(selected_date=date)
    await state.set_state(BookingStates.selecting_time)
    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d")
    date_fmt = dt.strftime("%d.%m.%Y")
    text = f"<b>🕐 Выберите время на {date_fmt}:</b>"
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_time_slots_keyboard(slots, date),
    )
    await callback.answer()


# === Выбор времени ===
@router.callback_query(F.data.startswith("time_"), BookingStates.selecting_time)
async def select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени -> запрос имени"""
    # callback_data: time_2025-03-15_10:00
    parts = callback.data.replace("time_", "").split("_", 1)
    date, time = parts[0], parts[1]
    await state.update_data(selected_date=date, selected_time=time)
    await state.set_state(BookingStates.entering_name)
    _get_booking_data(callback.from_user.id)["date"] = date
    _get_booking_data(callback.from_user.id)["time"] = time
    text = (
        f"<b>📝 Введите ваше имя</b>\n\n"
        f"📅 Дата: <b>{date}</b>\n🕐 Время: <b>{time}</b>"
    )
    await callback.message.edit_text(text=text, parse_mode="HTML")
    await callback.answer()


# === Ввод имени ===
@router.message(BookingStates.entering_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    """Получение имени -> запрос телефона"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя (не менее 2 символов)")
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer("📞 Введите номер телефона:")


# === Ввод телефона ===
@router.message(BookingStates.entering_phone, F.text)
async def enter_phone(message: Message, state: FSMContext):
    """Получение телефона -> подтверждение"""
    phone = message.text.strip()
    if len(phone) < 10:
        await message.answer("Пожалуйста, введите корректный номер телефона")
        return
    data = await state.get_data()
    date = data.get("selected_date")
    time = data.get("selected_time")
    name = data.get("client_name")
    await state.update_data(client_phone=phone)
    await state.set_state(BookingStates.confirming)

    from datetime import datetime
    dt = datetime.strptime(date, "%Y-%m-%d")
    date_fmt = dt.strftime("%d.%m.%Y")
    text = (
        f"<b>✅ Подтвердите запись</b>\n\n"
        f"📅 Дата: <b>{date_fmt}</b>\n"
        f"🕐 Время: <b>{time}</b>\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📞 Телефон: <b>{phone}</b>"
    )
    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard(date, time),
    )


# === Подтверждение записи ===
@router.callback_query(F.data.startswith("confirm_"), BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Сохранение записи в БД и уведомления"""
    # callback_data: confirm_2025-03-15_10:00
    data = await state.get_data()
    parts = callback.data.replace("confirm_", "").split("_", 1)
    if len(parts) == 2:
        date, time = parts[0], parts[1]  # 2025-03-15, 10:00
    else:
        date = data.get("selected_date")
        time = data.get("selected_time")
    name = data.get("client_name")
    phone = data.get("client_phone")
    user_id = callback.from_user.id

    db = get_db()
    booking_id = db.create_booking(user_id, date, time, name, phone)
    if not booking_id:
        await callback.answer("К сожалению, это время уже занято. Выберите другое.", show_alert=True)
        await state.clear()
        await callback.message.edit_text("Запись не выполнена.", reply_markup=get_main_menu_keyboard(user_id))
        return

    # Планируем напоминание за 24ч
    schedule_reminder(booking_id, user_id, date, time)

    # Сообщение пользователю
    dt = __import__("datetime").datetime.strptime(date, "%Y-%m-%d")
    date_fmt = dt.strftime("%d.%m.%Y")
    text = (
        f"<b>✅ Запись успешно создана!</b>\n\n"
        f"📅 Дата: <b>{date_fmt}</b>\n"
        f"🕐 Время: <b>{time}</b>\n\n"
        "Вы получите напоминание за 24 часа до визита.\n"
        "Для отмены используйте кнопку «Отменить запись»."
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(user_id))

    # Уведомление админу
    admin_text = (
        f"<b>📥 Новая запись!</b>\n\n"
        f"👤 {name}\n"
        f"📞 {phone}\n"
        f"📅 {date_fmt} в {time}\n"
        f"ID: {user_id}"
    )
    try:
        await callback.bot.send_message(config.ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception:
        pass

    # Публикация в канал
    try:
        channel_text = (
            f"📅 <b>Расписание</b>\n\n"
            f"{date_fmt} — {time}\n"
            f"👤 {name}"
        )
        await callback.bot.send_message(config.CHANNEL_ID, channel_text, parse_mode="HTML")
    except Exception:
        pass

    await state.clear()
    await callback.answer("Запись создана!")


# === Отмена записи пользователем ===
@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_user(callback: CallbackQuery, state: FSMContext):
    """Отмена своей записи"""
    await state.clear()
    user_id = callback.from_user.id
    db = get_db()
    booking = db.cancel_booking(user_id=user_id)
    if booking:
        cancel_reminder(booking["id"])
        text = "✅ Ваша запись успешно отменена. Слот снова доступен для записи."
    else:
        text = "У вас нет активных записей."
    user_id = callback.from_user.id if callback.from_user else None
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(user_id))
    await callback.answer()