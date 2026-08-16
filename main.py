import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import BOT_TOKEN
from database import init_db, register_user

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    chat = message.chat
    
    # Регистрируем пользователя и привязываем к чату
    register_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        chat_id=chat.id
    )
    
    if chat.type in ["group", "supergroup"]:
        await message.answer(
            f"Привет, {user.first_name}!\n"
            f"Бот успешно активирован в этой группе. Данные и XP сохраняются для каждого чата отдельно."
        )
    else:
        await message.answer(
            f"Привет, {user.first_name}!\n"
            f"Я универсальный игровой бот-помощник для групп. Добавьте меня в чат, чтобы начать играть и использовать модерацию!"
        )

async def main() -> None:
    # Инициализируем базу данных при запуске
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
