# -*- coding: utf-8 -*-
"""
Inline-клавиатуры для бота
"""
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Главное меню. user_id — для отображения кнопки админа."""
    import config
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Записаться", callback_data="booking_start"),
        InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Прайсы", callback_data="prices"),
        InlineKeyboardButton(text="📸 Портфолио", callback_data="portfolio"),
    )
    if user_id and user_id == config.ADMIN_ID:
        builder.row(InlineKeyboardButton(text="⚙️ Админ", callback_data="admin_panel"))
    return builder.as_markup()


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить рабочий день", callback_data="admin_add_day"),
        InlineKeyboardButton(text="🕐 Добавить слоты", callback_data="admin_add_slots"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить слот", callback_data="admin_remove_slot"),
        InlineKeyboardButton(text="🚫 Закрыть день", callback_data="admin_close_day"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Расписание на дату", callback_data="admin_view_schedule"),
        InlineKeyboardButton(text="❌ Отменить запись клиента", callback_data="admin_cancel_booking"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"),
    )
    return builder.as_markup()


def get_calendar_keyboard(dates: list, page: int = 0, per_page: int = 12) -> InlineKeyboardMarkup:
    """
    Клавиатура с календарём (даты).
    dates - список дат в формате YYYY-MM-DD
    """
    builder = InlineKeyboardBuilder()
    start = page * per_page
    end = min(start + per_page, len(dates))

    for i in range(start, end):
        date_str = dates[i]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        btn_text = dt.strftime("%d.%m (%a)")  # 15.03 (Fri)
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"date_{date_str}")
        )

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"calendar_page_{page - 1}")
        )
    if end < len(dates):
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"calendar_page_{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="back_to_main"))
    return builder.as_markup()


def get_time_slots_keyboard(slots: list, date: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    builder = InlineKeyboardBuilder()
    # Разбиваем на ряды по 3 кнопки
    for i in range(0, len(slots), 3):
        row_btns = []
        for j in range(3):
            if i + j < len(slots):
                time_str = slots[i + j]
                row_btns.append(
                    InlineKeyboardButton(
                        text=time_str,
                        callback_data=f"time_{date}_{time_str}",
                    )
                )
        builder.row(*row_btns)
    builder.row(InlineKeyboardButton(text="◀️ Назад к датам", callback_data="booking_start"))
    return builder.as_markup()


def get_confirm_keyboard(date: str, time: str) -> InlineKeyboardMarkup:
    """Подтверждение записи"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{date}_{time}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="booking_start"),
    )
    return builder.as_markup()


def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура проверки подписки"""
    import config
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Подписаться", url=config.CHANNEL_LINK),
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription"),
    )
    return builder.as_markup()


def get_portfolio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура портфолио"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Смотреть портфолио",
            url="https://ru.pinterest.com/crystalwithluv/_created/",
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    return builder.as_markup()


# === Админ-клавиатуры ===

def get_admin_calendar_keyboard(dates: list, prefix: str, page: int = 0) -> InlineKeyboardMarkup:
    """Календарь для админа (выбор даты для разных действий)"""
    builder = InlineKeyboardBuilder()
    per_page = 10
    start = page * per_page
    end = min(start + per_page, len(dates))

    for i in range(start, end):
        date_str = dates[i]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        btn_text = dt.strftime("%d.%m.%Y")
        builder.row(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"{prefix}_{date_str}",
            )
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️", callback_data=f"{prefix}_page_{page - 1}"
            )
        )
    if end < len(dates):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️", callback_data=f"{prefix}_page_{page + 1}"
            )
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_menu"))
    return builder.as_markup()


def get_admin_slot_keyboard(date: str, slots: list, action: str = "remove") -> InlineKeyboardMarkup:
    """Выбор слота для удаления"""
    builder = InlineKeyboardBuilder()
    for time in slots:
        builder.row(
            InlineKeyboardButton(
                text=time,
                callback_data=f"admin_{action}_slot_{date}_{time}",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"))
    return builder.as_markup()


def get_admin_booking_keyboard(bookings: list) -> InlineKeyboardMarkup:
    """Список записей для отмены админом"""
    builder = InlineKeyboardBuilder()
    for b in bookings:
        text = f"{b['date']} {b['time']} - {b['client_name']}"
        builder.row(
            InlineKeyboardButton(
                text=text[:40],
                callback_data=f"admin_cancel_{b['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"))
    return builder.as_markup()
