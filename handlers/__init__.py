# -*- coding: utf-8 -*-
"""
Обработчики бота
"""
from aiogram import Router
from .user import router as user_router
from .admin import router as admin_router
from .common import router as common_router


def register_routers():
    """Создание и регистрация всех роутеров"""
    main_router = Router()
    main_router.include_router(common_router)
    main_router.include_router(user_router)
    main_router.include_router(admin_router)
    return main_router
