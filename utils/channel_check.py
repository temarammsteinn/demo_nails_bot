# -*- coding: utf-8 -*-
"""
Проверка подписки на канал
"""
from aiogram import Bot
from aiogram.enums import ChatMemberStatus

import config


async def check_channel_subscription(bot: Bot, user_id: int) -> bool:
    """
    Проверить, подписан ли пользователь на канал.
    Возвращает True если подписан, False если нет.
    """
    try:
        member = await bot.get_chat_member(
            chat_id=config.CHANNEL_ID,
            user_id=user_id,
        )
        # Подписан если status: member, administrator, creator
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False
