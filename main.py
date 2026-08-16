import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        "Привет! Ты можешь добавить меня в группу, я буду твоим помощником там."
    )

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
