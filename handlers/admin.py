# -*- coding: utf-8 -*-
"""
Админ-панель: управление расписанием и записями
"""
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import config
from database import get_db
from keyboards.inline import (
    get_main_menu_keyboard,
    get_admin_menu_keyboard,
    get_admin_calendar_keyboard,
    get_admin_slot_keyboard,
    get_admin_booking_keyboard,
)
from handlers.states import AdminStates
from utils.scheduler import cancel_reminder

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка доступа админа"""
    return user_id == config.ADMIN_ID


# === Команда /admin и кнопка админ-панели ===
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Открыть админ-панель"""
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "<b>⚙️ Админ-панель</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    """Открыть админ-панель по кнопке"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "<b>⚙️ Админ-панель</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu_keyboard(),
    )
    await callback.answer()


# === Кнопка админ-панели (для входа из главного меню - можно добавить) ===
# Админ заходит через /admin

# === Админ: Назад ===
@router.callback_query(F.data == "admin_menu")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    """Вернуться в админ-меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "<b>⚙️ Админ-панель</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu_keyboard(),
    )
    await callback.answer()


# === Добавить рабочий день ===
@router.callback_query(F.data == "admin_add_day")
async def admin_add_day_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления рабочего дня"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminStates.adding_day)
    await callback.message.edit_text(
        "📅 Введите дату в формате <b>ГГГГ-ММ-ДД</b> (например, 2025-03-15):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.adding_day, F.text)
async def admin_add_day_process(message: Message, state: FSMContext):
    """Обработка введённой даты"""
    if not is_admin(message.from_user.id):
        return
    try:
        dt = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        date_str = dt.strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        if date_str < today:
            await message.answer("Нельзя добавить прошедшую дату.")
            return
        db = get_db()
        db.add_working_day(date_str)
        db.generate_slots_for_day(
            date_str,
            config.DEFAULT_WORK_START,
            config.DEFAULT_WORK_END,
            config.DEFAULT_SLOT_DURATION,
        )
        await message.answer(
            f"✅ Рабочий день {date_str} добавлен со стандартными слотами.",
            reply_markup=get_admin_menu_keyboard(),
        )
    except ValueError:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД.")
    await state.clear()


# === Добавить слоты ===
@router.callback_query(F.data == "admin_add_slots")
async def admin_add_slots_start(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для добавления слотов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    conn = db._get_connection()
    cursor = conn.execute(
        "SELECT date FROM working_days WHERE date >= ? AND date <= ? ORDER BY date",
        (today, end),
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not dates:
        await callback.message.edit_text("Нет рабочих дней. Сначала добавьте день.")
        await callback.answer()
        return
    await state.set_state(AdminStates.adding_slots_date)
    await callback.message.edit_text(
        "📅 Выберите дату для добавления слота:",
        reply_markup=get_admin_calendar_keyboard(dates, "admin_addslots", 0),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_addslots_"), AdminStates.adding_slots_date)
async def admin_add_slots_date(callback: CallbackQuery, state: FSMContext):
    """Выбрана дата - ввод времени"""
    if not is_admin(callback.from_user.id):
        return
    suffix = callback.data.replace("admin_addslots_", "")
    if suffix.startswith("page_"):
        page = int(suffix.split("_")[-1])
        db = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT date FROM working_days WHERE date >= ? AND date <= ? ORDER BY date",
            (today, end),
        )
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_calendar_keyboard(dates, "admin_addslots", page),
        )
        await callback.answer()
        return
    date = suffix
    await state.update_data(admin_slots_date=date)
    await state.set_state(AdminStates.adding_slots_time)
    await callback.message.edit_text(
        f"🕐 Введите время слота в формате <b>ЧЧ:ММ</b> (например, 14:00) для даты {date}:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.adding_slots_time, F.text)
async def admin_add_slot_time(message: Message, state: FSMContext):
    """Добавление слота по времени"""
    if not is_admin(message.from_user.id):
        return
    try:
        datetime.strptime(message.text.strip(), "%H:%M")
        time_str = message.text.strip()
        data = await state.get_data()
        date = data.get("admin_slots_date")
        db = get_db()
        db.add_slot(date, time_str)
        await message.answer(
            f"✅ Слот {time_str} добавлен на {date}.",
            reply_markup=get_admin_menu_keyboard(),
        )
    except ValueError:
        await message.answer("Неверный формат. Используйте ЧЧ:ММ.")
    await state.clear()


# === Удалить слот ===
@router.callback_query(F.data == "admin_remove_slot")
async def admin_remove_slot_start(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для удаления слота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    conn = db._get_connection()
    cursor = conn.execute(
        "SELECT DISTINCT date FROM slots WHERE date >= ? ORDER BY date LIMIT 90",
        (today,),
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not dates:
        await callback.message.edit_text("Нет слотов для удаления.")
        await callback.answer()
        return
    await state.set_state(AdminStates.removing_slot_date)
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=get_admin_calendar_keyboard(dates, "admin_removeslot", 0),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_removeslot_"), AdminStates.removing_slot_date)
async def admin_remove_slot_date(callback: CallbackQuery, state: FSMContext):
    """Выбор слота для удаления"""
    if not is_admin(callback.from_user.id):
        return
    suffix = callback.data.replace("admin_removeslot_", "")
    if suffix.startswith("page_"):
        page = int(suffix.split("_")[-1])
        db = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT DISTINCT date FROM slots WHERE date >= ? ORDER BY date LIMIT 90",
            (today,),
        )
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_calendar_keyboard(dates, "admin_removeslot", page),
        )
        await callback.answer()
        return
    date = suffix
    db = get_db()
    slots = db.get_all_slots_for_date(date)
    if not slots:
        await callback.answer("Нет слотов на эту дату", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🕐 Выберите слот для удаления:",
        reply_markup=get_admin_slot_keyboard(date, slots, "remove"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove_slot_"))
async def admin_remove_slot_confirm(callback: CallbackQuery):
    """Удаление выбранного слота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    parts = callback.data.replace("admin_remove_slot_", "").split("_", 1)
    if len(parts) == 2:
        date, time = parts[0], parts[1]
        db = get_db()
        db.remove_slot(date, time)
        await callback.message.edit_text(f"✅ Слот {time} на {date} удалён.")
    await callback.answer()


# === Закрыть день ===
@router.callback_query(F.data == "admin_close_day")
async def admin_close_day_start(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для закрытия"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    conn = db._get_connection()
    cursor = conn.execute(
        "SELECT date FROM working_days WHERE date >= ? AND is_closed = 0 ORDER BY date LIMIT 60",
        (today,),
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not dates:
        await callback.message.edit_text("Нет дней для закрытия.")
        await callback.answer()
        return
    await state.set_state(AdminStates.closing_day)
    await callback.message.edit_text(
        "📅 Выберите дату для закрытия:",
        reply_markup=get_admin_calendar_keyboard(dates, "admin_closeday", 0),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_closeday_"), AdminStates.closing_day)
async def admin_close_day_confirm(callback: CallbackQuery, state: FSMContext):
    """Закрытие дня"""
    if not is_admin(callback.from_user.id):
        return
    suffix = callback.data.replace("admin_closeday_", "")
    if suffix.startswith("page_"):
        page = int(suffix.split("_")[-1])
        db = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT date FROM working_days WHERE date >= ? AND is_closed = 0 ORDER BY date LIMIT 60",
            (today,),
        )
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_calendar_keyboard(dates, "admin_closeday", page),
        )
        await callback.answer()
        return
    date = suffix
    db = get_db()
    db.close_day(date)
    await state.clear()
    await callback.message.edit_text(f"✅ День {date} закрыт.")
    await callback.answer()


# === Расписание на дату ===
@router.callback_query(F.data == "admin_view_schedule")
async def admin_view_schedule_start(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для просмотра"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    conn = db._get_connection()
    cursor = conn.execute(
        "SELECT date FROM working_days WHERE date >= ? AND date <= ? ORDER BY date",
        (today, end),
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not dates:
        await callback.message.edit_text("Нет данных.")
        await callback.answer()
        return
    await state.set_state(AdminStates.viewing_schedule_date)
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=get_admin_calendar_keyboard(dates, "admin_view", 0),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_"), AdminStates.viewing_schedule_date)
async def admin_view_schedule_show(callback: CallbackQuery, state: FSMContext):
    """Показать расписание на дату"""
    if not is_admin(callback.from_user.id):
        return
    suffix = callback.data.replace("admin_view_", "")
    if suffix.startswith("page_"):
        page = int(suffix.split("_")[-1])
        db = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT date FROM working_days WHERE date >= ? AND date <= ? ORDER BY date",
            (today, end),
        )
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_calendar_keyboard(dates, "admin_view", page),
        )
        await callback.answer()
        return
    date = suffix
    db = get_db()
    slots = db.get_slots_for_admin(date)
    lines = [f"<b>📋 Расписание на {date}</b>\n"]
    for s in slots:
        if s["is_available"]:
            status = "✅ Свободно"
        else:
            name = s.get("client_name") or "—"
            phone = s.get("client_phone") or "—"
            status = f"❌ {name} ({phone})"
        lines.append(f"{s['time']} — {status}")
    await state.clear()
    await callback.message.edit_text(
        "\n".join(lines) if lines else "Нет слотов.",
        parse_mode="HTML",
        reply_markup=get_admin_menu_keyboard(),
    )
    await callback.answer()


# === Отменить запись клиента ===
@router.callback_query(F.data == "admin_cancel_booking")
async def admin_cancel_booking_start(callback: CallbackQuery, state: FSMContext):
    """Выбор записи для отмены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    conn = db._get_connection()
    cursor = conn.execute(
        "SELECT id, date, time, client_name, client_phone FROM bookings WHERE date >= ? ORDER BY date, time",
        (today,),
    )
    bookings = [dict(zip(("id", "date", "time", "client_name", "client_phone"), row)) for row in cursor.fetchall()]
    conn.close()
    if not bookings:
        await callback.message.edit_text("Нет активных записей.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выберите запись для отмены:",
        reply_markup=get_admin_booking_keyboard(bookings),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel_booking_confirm(callback: CallbackQuery):
    """Отмена выбранной записи"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    try:
        booking_id = int(callback.data.replace("admin_cancel_", ""))
    except ValueError:
        await callback.answer()
        return
    db = get_db()
    booking = db.cancel_booking(booking_id=booking_id)
    if booking:
        cancel_reminder(booking_id)
        await callback.message.edit_text("✅ Запись отменена. Слот снова доступен.")
    else:
        await callback.answer("Запись не найдена", show_alert=True)
    await callback.answer()
