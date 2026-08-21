import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto,
    FSInputFile
)

logging.basicConfig(level=logging.INFO)

MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
ADMIN_ID = 5208615220 

bot = Bot(token=MAIN_BOT_TOKEN)
support_bot = Bot(token=SUPPORT_BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())
support_dp = Dispatcher(storage=MemoryStorage())

# --- FSM СОСТОЯНИЯ ТОЛЬКО ДЛЯ АДМИНА ---
class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

# --- ФАЙЛЫ КАРТИНОК ИЗ КОРНЯ РЕПОЗИТОРИЯ ---
PHOTO_START = "start.PNG"
PHOTO_VPN = "vpn.PNG"
PHOTO_SUPPORT = "support.PNG"
PHOTO_REFERRAL = "referral.PNG"

# --- ХРАНИЛИЩЕ ПОДПИСОК И ГЛОБАЛЬНЫЙ СЧЕТЧИК НОМЕРОВ ---
USER_SUBSCRIPTIONS = {}  # user_id -> list of subscription dicts
GLOBAL_SUBSCRIPTION_COUNTER = 1  # Глобальный сквозной счетчик подписок

# --- ВАШ ТЕСТОВЫЙ КЛЮЧ ДЛЯ ДЕМОНСТРАЦИИ ---
DEMO_TEST_KEY = "vless://вставьте-сюда-ваш-реальный-ключ-из-другого-бота@server:port?security=reality"

# --- ИНЛАЙН КЛАВИАТУРЫ ---

def get_start_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Управление VPN", callback_data="to_vpn_manage")],
        [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="to_referral_cb")],
        [InlineKeyboardButton(text="🆘 Помощь / Поддержка", callback_data="to_support_cb"), InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="to_about_cb")]
    ])

def get_vpn_manage_keyboard(user_id: int):
    subs = USER_SUBSCRIPTIONS.get(user_id, [])
    active_subs = [s for s in subs if s.get("active", False)]
    has_active = len(active_subs) > 0

    keyboard = []

    if has_active:
        keyboard.append([InlineKeyboardButton(text="📂 Подписки", callback_data="show_my_subscriptions")])
        keyboard.append([InlineKeyboardButton(text="➕ Добавить подписку", callback_data="buy_devices")])
    else:
        keyboard.append([InlineKeyboardButton(text="⚡ Получить тестовый период (3 дня)", callback_data="get_trial")])
        keyboard.append([InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_devices")])
    
    keyboard.append([InlineKeyboardButton(text="‹ Назад", callback_data="to_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_devices_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 2 устройства (от 99 ₽/мес)", callback_data="dev_2")],
        [InlineKeyboardButton(text="📱📱 5 устройств (от 149 ₽/мес)", callback_data="dev_5")],
        [InlineKeyboardButton(text="💻 10 устройств (от 249 ₽/мес)", callback_data="dev_10")],
        [InlineKeyboardButton(text="‹ Назад в управление", callback_data="to_vpn_manage")]
    ])

def get_period_keyboard(dev_count: int):
    prices = {
        2: ("149 ₽", "349 ₽", "1190 ₽"),
        5: ("190 ₽", "490 ₽", "1490 ₽"),
        10: ("290 ₽", "690 ₽", "2190 ₽")
    }
    p1, p3, p12 = prices.get(dev_count, prices[2])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1 месяц — {p1}", callback_data=f"pay_{dev_count}_1")],
        [InlineKeyboardButton(text=f"3 месяца — {p3}", callback_data=f"pay_{dev_count}_3")],
        [InlineKeyboardButton(text=f"12 месяцев — {p12} 🔥", callback_data=f"pay_{dev_count}_12")],
        [InlineKeyboardButton(text="‹ Назад к выбору устройств", callback_data="buy_devices")]
    ])

def get_payment_keyboard(dev_count: int, period: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Банковская карта / СБП (Тест 30 мин)", callback_data=f"process_pay_{dev_count}_{period}")],
        [InlineKeyboardButton(text="‹ Назад к выбору периода", callback_data=f"dev_{dev_count}")]
    ])

def get_support_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Как подключить VPN?", callback_data="sup_connect")],
        [InlineKeyboardButton(text="⚠️ Если VPN не подключается", callback_data="sup_error")],
        [InlineKeyboardButton(text="💳 Вопросы по оплате", callback_data="sup_pay")],
        [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/ArvellaSupportBOT")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="to_main")]
    ])

def get_back_to_support_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="‹ Назад", callback_data="to_support_cb")]
    ])

def get_about_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Наш Telegram-канал", url="https://t.me/ArvellaVPN")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="to_main")]
    ])

# --- ФОНОВАЯ ЗАДАЧА ДЛЯ АВТОМАТИЧЕСКОГО ОТКЛЮЧЕНИЯ КОНКРЕТНОЙ ПОДПИСКИ ---

async def schedule_subscription_expiry(user_id: int, sub_index: int, delay_seconds: int = 1800):
    await asyncio.sleep(delay_seconds)
    subs = USER_SUBSCRIPTIONS.get(user_id, [])
    if sub_index < len(subs):
        subs[sub_index]["active"] = False
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"⏰ <b>Время тестового доступа для подписки #{subs[sub_index]['number']} истекло.</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def delete_previous_message(state: FSMContext, chat_id: int):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
        except Exception:
            pass

# --- ХЕНДЛЕРЫ ОСНОВНОГО БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await delete_previous_message(state, message.chat.id)
    try: await message.delete()
    except Exception: pass
    
    text = (
        "<b>Добро пожаловать в Arvella VPN ❤️‍🔥</b>\n\n"
        "VPN, который работает там, где глушат остальные.\n"
        "Забудь про бесконечную загрузку: YouTube в 4K, Instagram, ChatGPT, банковские приложения и любые сайты — "
        "всё открывается моментально, без рекламы и обрывов.\n\n"
        "Свободный интернет. Таким, каким он должен быть."
    )
    
    temp_msg = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await temp_msg.delete()

    msg = await message.answer_photo(
        photo=FSInputFile(PHOTO_START),
        caption=text,
        parse_mode="HTML",
        reply_markup=get_start_inline_keyboard()
    )
    await state.update_data(last_msg_id=msg.message_id)

@dp.callback_query(F.data == "to_referral_cb")
async def cb_to_referral(call: types.CallbackQuery, state: FSMContext):
    ref_link = f"https://t.me/ArvellaVPN_bot?start=ref{call.from_user.id}"
    text = (
        "🎁 <b>Реферальная программа</b>\n\n"
        "Делитесь личной ссылкой с друзьями и получайте +7 дней бесплатной подписки за каждого, кто подключится по вашей рекомендации!\n\n"
        "📊 <b>Ваша статистика:</b>\n• Приглашено: 0 чел.\n• Заработано: 0 дней\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", switch_inline_query=ref_link)],
        [InlineKeyboardButton(text="‹ Назад", callback_data="to_main")]
    ])
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_REFERRAL), caption=text, parse_mode="HTML"),
        reply_markup=kb
    )

@dp.callback_query(F.data == "to_support_cb")
async def cb_to_support(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🆘 <b>Инструкция и помощь</b>\n\n"
        "Выберите интересующий вас вопрос или напишите в поддержку:"
    )
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_SUPPORT), caption=text, parse_mode="HTML"),
        reply_markup=get_support_keyboard()
    )

@dp.callback_query(F.data == "sup_connect")
async def cb_sup_connect(call: types.CallbackQuery):
    text = (
        "💡 <b>Как подключить VPN:</b>\n\n"
        "• Скачайте приложение Happ (или v2rayNG / Streisand).\n"
        "• Скопируйте VLESS-ключ, который выдан вам в управлении VPN.\n"
        "• Зайдите в приложение и добавьте ключ из буфера обмена.\n"
        "• Нажмите кнопку Старт для подключения."
    )
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_SUPPORT), caption=text, parse_mode="HTML"),
        reply_markup=get_back_to_support_keyboard()
    )

@dp.callback_query(F.data == "sup_error")
async def cb_sup_error(call: types.CallbackQuery):
    text = (
        "⚠️ <b>Если VPN не подключается:</b>\n\n"
        "• Проверьте, включен ли мобильный интернет или Wi-Fi.\n"
        "• Переключите сервер или обновите конфигурацию в приложении.\n"
        "• Попробуйте включить/выключить авиарежим на 5 секунд."
    )
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_SUPPORT), caption=text, parse_mode="HTML"),
        reply_markup=get_back_to_support_keyboard()
    )

@dp.callback_query(F.data == "sup_pay")
async def cb_sup_pay(call: types.CallbackQuery):
    text = (
        "💳 <b>Вопросы по оплате:</b>\n\n"
        "Подписка активируется автоматически в течение 1–2 минут после совершения платежа."
    )
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_SUPPORT), caption=text, parse_mode="HTML"),
        reply_markup=get_back_to_support_keyboard()
    )

@dp.callback_query(F.data == "to_about_cb")
async def cb_to_about(call: types.CallbackQuery):
    text = (
        "ℹ️ <b>О сервисе Arvella VPN</b>\n\n"
        "Arvella VPN — это приватный и высокоскоростной доступ в интернет на базе протокола VLESS (XTLS-Reality).\n\n"
        "• <b>Максимальная маскировка:</b> Трафик выглядит как посещение обычных сайтов.\n"
        "• <b>Высокая скорость:</b> Сервера с каналом до 1 Гбит/с.\n"
        "• <b>Без логов:</b> Мы не храним историю вашей активности."
    )
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=get_about_keyboard())

@dp.callback_query(F.data == "show_my_subscriptions")
async def cb_show_my_subscriptions(call: types.CallbackQuery):
    user_id = call.from_user.id
    subs = USER_SUBSCRIPTIONS.get(user_id, [])
    
    keyboard = []
    for idx, sub in enumerate(subs):
        status_emoji = "🟢" if sub.get("active", False) else "🔴"
        keyboard.append([InlineKeyboardButton(
            text=f"{status_emoji} Подписка #{sub['number']}", 
            callback_data=f"manage_sub_{idx}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="‹ Назад в управление", callback_data="to_vpn_manage")])
    
    text = "📂 <b>Ваши подписки</b>\n\nВыберите нужную подписку для просмотра ключа:"
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(F.data.startswith("manage_sub_"))
async def cb_manage_subscription(call: types.CallbackQuery):
    user_id = call.from_user.id
    sub_idx = int(call.data.split("_")[2])
    subs = USER_SUBSCRIPTIONS.get(user_id, [])
    
    if sub_idx >= len(subs):
        await call.answer("Подписка не найдена.", show_alert=True)
        return
        
    sub = subs[sub_idx]
    vless_key = sub.get("key", DEMO_TEST_KEY)
    status_text = "Активна 🟢" if sub.get("active", False) else "Неактивна 🔴"
    
    text = (
        f"📂 <b>Подписка #{sub['number']}</b>\n"
        f"• Статус: {status_text}\n"
        f"• Устройств: {sub.get('devices', 2)}\n\n"
        f"🔑 <b>VLESS-ключ:</b>\n<code>{vless_key}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Подключить в 1 клик", url=f"happ://import/{vless_key}")],
        [InlineKeyboardButton(text="‹ К списку подписок", callback_data="show_my_subscriptions")]
    ])
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=kb
    )

@dp.callback_query(F.data == "to_vpn_manage")
async def cb_to_vpn_manage(call: types.CallbackQuery):
    user_id = call.from_user.id
    text = "🏠 <b>Главная › 🛒 Управление VPN</b>\n\nВыберите действие с вашим профилем подписки:"
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=get_vpn_manage_keyboard(user_id)
    )

@dp.callback_query(F.data == "get_trial")
async def cb_get_trial(call: types.CallbackQuery):
    global GLOBAL_SUBSCRIPTION_COUNTER
    user_id = call.from_user.id
    vless_key = DEMO_TEST_KEY
    
    sub_number = GLOBAL_SUBSCRIPTION_COUNTER
    GLOBAL_SUBSCRIPTION_COUNTER += 1

    if user_id not in USER_SUBSCRIPTIONS:
        USER_SUBSCRIPTIONS[user_id] = []
    
    USER_SUBSCRIPTIONS[user_id].append({
        "number": sub_number,
        "active": True,
        "devices": 2,
        "period": 3,
        "key": vless_key
    })

    sub_index = len(USER_SUBSCRIPTIONS[user_id]) - 1
    asyncio.create_task(schedule_subscription_expiry(user_id, sub_index, delay_seconds=1800))

    text = (
        f"🎁 <b>Пробный период (3 дня) для подписки #{sub_number} успешно активирован!</b>\n\n"
        f"🔑 <b>Ваш ключ:</b>\n<code>{vless_key}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Подключить в 1 клик", url=f"happ://import/{vless_key}")],
        [InlineKeyboardButton(text="‹ В управление VPN", callback_data="to_vpn_manage")]
    ])
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=kb
    )

@dp.callback_query(F.data == "buy_devices")
async def cb_buy_devices(call: types.CallbackQuery):
    text = "📱 <b>Выберите количество устройств</b>\n\nПодписка будет работать одновременно на всех ваших устройствах:"
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=get_devices_keyboard()
    )

@dp.callback_query(F.data.startswith("dev_"))
async def cb_select_devices(call: types.CallbackQuery):
    dev_count = int(call.data.split("_")[1])
    text = f"💳 <b>Подписка на {dev_count} устройств</b>\n\nВыберите период подписки:"
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=get_period_keyboard(dev_count)
    )

@dp.callback_query(F.data.startswith("pay_"))
async def cb_select_period(call: types.CallbackQuery):
    _, dev_count, period = call.data.split("_")
    dev_count, period = int(dev_count), int(period)
    
    prices = {2: {1: 149, 3: 349, 12: 1190}, 5: {1: 190, 3: 490, 12: 1490}, 10: {1: 290, 3: 690, 12: 2190}}
    price = prices[dev_count][period]

    text = (
        "💳 <b>Оплата подписки Arvella VPN</b>\n\n"
        f"• <b>Устройств:</b> {dev_count}\n"
        f"• <b>Период:</b> {period} мес.\n"
        f"• <b>К оплате:</b> {price} ₽\n\n"
        "Нажмите кнопку ниже для тестовой эмуляции оплаты (выдаст реальный ключ на 30 минут):"
    )
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=get_payment_keyboard(dev_count, period)
    )

@dp.callback_query(F.data.startswith("process_pay_"))
async def cb_process_payment(call: types.CallbackQuery):
    global GLOBAL_SUBSCRIPTION_COUNTER
    user_id = call.from_user.id
    _, _, dev_count, period = call.data.split("_")
    dev_count, period = int(dev_count), int(period)

    vless_key = DEMO_TEST_KEY
    sub_number = GLOBAL_SUBSCRIPTION_COUNTER
    GLOBAL_SUBSCRIPTION_COUNTER += 1

    if user_id not in USER_SUBSCRIPTIONS:
        USER_SUBSCRIPTIONS[user_id] = []

    USER_SUBSCRIPTIONS[user_id].append({
        "number": sub_number,
        "active": True,
        "devices": dev_count,
        "period": period,
        "key": vless_key
    })

    sub_index = len(USER_SUBSCRIPTIONS[user_id]) - 1
    asyncio.create_task(schedule_subscription_expiry(user_id, sub_index, delay_seconds=1800))

    text = (
        f"✅ <b>Тестовая оплата прошла успешно! Подписка #{sub_number} активна на 30 минут.</b>\n\n"
        f"🔑 <b>Ваш ключ подключения:</b>\n<code>{vless_key}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Подключить в 1 клик", url=f"happ://import/{vless_key}")],
        [InlineKeyboardButton(text="🏠 В управление VPN", callback_data="to_vpn_manage")]
    ])
    await call.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(PHOTO_VPN), caption=text, parse_mode="HTML"),
        reply_markup=kb
    )

@dp.callback_query(F.data == "to_main")
async def cb_to_main(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
    except Exception:
        pass
    await cmd_start(call.message, state)


# --- ХЕНДЛЕРЫ В БОТЕ ПОДДЕРЖКИ (SUPPORT BOT) ---

@support_dp.message(Command("start"))
async def support_cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🤖 Служебный бот поддержки активен. Сюда приходят обращения от пользователей.")
    else:
        await message.answer("✍️ Отправьте ваше сообщение или скриншот проблемы, и администратор ответит вам прямо здесь.")

@support_dp.message(F.from_user.id != ADMIN_ID)
async def forward_user_to_admin(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "нет"

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_to_{user_id}")]
    ])

    try:
        if message.photo:
            await support_bot.send_photo(
                chat_id=ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=f"📩 <b>Обращение от {user_name} ({username})</b>\nID: <code>{user_id}</code>\nПодпись: {message.caption or 'Нет'}",
                parse_mode="HTML",
                reply_markup=reply_kb
            )
        else:
            await support_bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 <b>Обращение от {user_name} ({username})</b>\nID: <code>{user_id}</code>\nТекст: {message.text}",
                parse_mode="HTML",
                reply_markup=reply_kb
            )
        await message.answer("✅ Сообщение отправлено в поддержку! Ожидайте ответа.")
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")
        await message.answer("❌ Не удалось отправить сообщение.")

@support_dp.callback_query(F.data.startswith("reply_to_"))
async def cb_admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    call_user_id = getattr(call.from_user, "id", None)
    if call_user_id != ADMIN_ID:
        await call.answer("У вас нет прав.", show_alert=True)
        return

    target_user_id = int(call.data.split("_")[2])
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    
    await call.message.reply(
        f"✍️ Напишите ответ для пользователя <code>{target_user_id}</code> (он придет ему в бот поддержки):",
        parse_mode="HTML"
    )
    await call.answer()

@support_dp.message(AdminReplyState.waiting_for_reply)
async def process_admin_reply_send(message: types.Message, state: FSMContext):
    msg_user_id = getattr(message.from_user, "id", None)
    if msg_user_id != ADMIN_ID:
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    await state.clear()

    reply_text = (
        "👨‍💻 <b>Ответ поддержки:</b>\n\n"
        f"{message.text}"
    )

    try:
        await support_bot.send_message(
            chat_id=target_user_id,
            text=reply_text,
            parse_mode="HTML"
        )
        await message.answer(f"✅ Ответ успешно доставлен пользователю <code>{target_user_id}</code>!", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Не удалось доставить сообщение.\nОшибка: {e}")


# --- ЗАПУСК ОБОИХ БОТОВ ОДНОВРЕМЕННО ---

async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        support_dp.start_polling(support_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
