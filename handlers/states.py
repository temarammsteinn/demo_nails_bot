# -*- coding: utf-8 -*-
"""
FSM-состояния для записи на приём
"""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса записи"""
    selecting_date = State()
    selecting_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    adding_day = State()
    adding_slots_date = State()
    adding_slots_time = State()
    removing_slot_date = State()
    closing_day = State()
    viewing_schedule_date = State()
    canceling_booking_select = State()
