import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatPermissions
from config import BOT_TOKEN
from database import init_db, get_connection, update_xp

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- СПРАВКА И РАЗДЕЛ «ЧТО Я УМЕЮ» ---
@dp.message(Command("помощь", "что_я_умею"))
async def help_handler(message: Message):
    help_text = (
        "🤖 **Я — ваш игровой бот-помощник!**\n\n"
        "🎮 **Игры и статистика:**\n"
        "• `/dice` — Бросить кубик и заработать XP\n"
        "• `/профиль` — Посмотреть свой уровень и опыт (скоро)\n"
        "• `/рейтинг` — Топ игроков группы (скоро)\n\n"
        "🛡 **Модерация (для администраторов):**\n"
        "• `/мут` — Ограничить отправку сообщений (ответом)\n"
        "• `/размут` — Снять ограничения (ответом)\n"
        "• `/бан` — Заблокировать участника (ответом)\n"
        "• `/антистикер` — Запретить стикеры пользователю (ответом)\n\n"
        "⚙️ **Автоматические функции:**\n"
        "• Автоматически удаляет стикеры у пользователей, попавших под ограничение."
    )
    await message.answer(help_text, parse_mode="Markdown")

# --- СТАРТ ---
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    chat = message.chat
    
    if chat.type in ["group", "supergroup"]:
        await message.answer(
            f"Привет, {user.first_name}!\n"
            f"Бот-помощник активен в этой группе. Напишите /помощь, чтобы узнать возможности."
        )
    else:
        await message.answer(
            f"Ты нахуя нажал start? Ладно,привет, {user.first_name}!\n"
            f"Добавьте меня в группу, чтобы использовать игры, рейтинг и модерацию."
        )

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
        try:
            await message.chat.ban(user_id=message.reply_to_message.from_user.id)
            await message.answer("Пользователь забанен.")
        except Exception as e:
            await message.answer(f"Ошибка бана (проверьте права бота): {e}")
    else:
        await message.answer("Ответьте на сообщение пользователя, которого нужно забанить.")

@dp.message(Command("мут"))
async def mute_user(message: Message):
    if message.reply_to_message:
        try:
            await message.chat.restrict(
                user_id=message.reply_to_message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await message.answer("Этот долбаеб теперь в муте.")
        except Exception as e:
            await message.answer(f"Ошибка мута (проверьте права бота): {e}")
    else:
        await message.answer("Ответьте на сообщение пидораса, которого нужно замутить.")

@dp.message(Command("размут"))
async def unmute_user(message: Message):
    if message.reply_to_message:
        try:
            await message.chat.restrict(
                user_id=message.reply_to_message.from_user.id,
                permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True)
            )
            await message.answer("Мут снят.")
        except Exception as e:
            await message.answer(f"Ошибка размута: {e}")
    else:
        await message.answer("Ответьте на сообщение пидораса.")

@dp.message(Command("антистикер"))
async def anti_sticker_cmd(message: Message):
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO anti_sticker VALUES (?, ?)", (uid, message.chat.id))
        conn.commit()
        conn.close()
        await message.answer("Стикеры для пользователя запрещены.")
    else:
        await message.answer("Ответьте на сообщение пользователя, у которого нужно запретить стикеры.")

# --- АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ СТИКЕРОВ ---
@dp.message(F.sticker)
async def handle_stickers(message: Message):
    conn = get_connection()
    is_banned = conn.execute(
        "SELECT 1 FROM anti_sticker WHERE user_id=? AND chat_id=?", 
        (message.from_user.id, message.chat.id)
    ).fetchone()
    conn.close()
    
    if is_banned:
        try:
            await message.delete()
        except Exception:
            pass

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
