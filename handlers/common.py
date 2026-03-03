# -*- coding: utf-8 -*-
"""
Общие обработчики: Прайсы, Портфолио (без FSM)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import get_main_menu_keyboard, get_portfolio_keyboard

router = Router()


# === Прайсы ===
@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    """Показать прайс-лист"""
    text = (
        "<b>💰 Прайс-лист</b>\n\n"
        "Френч — 1000₽\n"
        "Квадрат — 500₽"
    )
    user_id = callback.from_user.id if callback.from_user else None
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(user_id),
    )
    await callback.answer()


# === Портфолио ===
@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery):
    """Показать портфолио с кнопкой-ссылкой"""
    text = "📸 Наши работы:"
    await callback.message.edit_text(
        text=text,
        reply_markup=get_portfolio_keyboard(),
    )
    await callback.answer()
