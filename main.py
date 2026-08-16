import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatPermissions
from config import BOT_TOKEN
from database import init_db, get_connection, update_xp

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- ИГРЫ ---
@dp.message(Command("dice"))
async def play_dice(message: Message):
    dice = await message.answer_dice(emoji="🎲")
    update_xp(message.from_user.id, message.chat.id, 10 + dice.dice.value * 2)
    await message.reply(f"Вы выбросили {dice.dice.value}. XP начислены!")

# --- МОДЕРАЦИЯ ---
@dp.message(Command("ban"))
async def ban_user(message: Message):
    if message.reply_to_message:
        await message.chat.ban(user_id=message.reply_to_message.from_user.id)
        await message.answer("Пользователь забанен.")

@dp.message(Command("мут"))
async def mute_user(message: Message):
    if message.reply_to_message:
        await message.chat.restrict(
            user_id=message.reply_to_message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await message.answer("Пользователь в муте.")

@dp.message(Command("размут"))
async def unmute_user(message: Message):
    if message.reply_to_message:
        await message.chat.restrict(
            user_id=message.reply_to_message.from_user.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True)
        )
        await message.answer("Мут снят.")

@dp.message(Command("антистикер"))
async def anti_sticker_cmd(message: Message):
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO anti_sticker VALUES (?, ?)", (uid, message.chat.id))
        conn.commit()
        await message.answer("Стикеры для пользователя запрещены.")

# --- УДАЛЕНИЕ СТИКЕРОВ ---
@dp.message(F.sticker)
async def handle_stickers(message: Message):
    conn = get_connection()
    is_banned = conn.execute("SELECT 1 FROM anti_sticker WHERE user_id=? AND chat_id=?", 
                             (message.from_user.id, message.chat.id)).fetchone()
    if is_banned:
        await message.delete()

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
