import asyncio
import json
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8610106870:AAFkYcmQZDic3dAygs47WuM9FlHlkwuBduk"
ADMINS = [5454985521]

DB_FILE = "whitelist.json"
STATS_FILE = "user_stats.json"
BAN_LOG_FILE = "ban_log.json"
# --------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

PATTERN = re.compile(r'(?i)\b(работ[а-я]*|темк[а-я]*|темок|подработ[а-я]*|заработ[а-я]*)\b')

# --- ФУНКЦИЯ ОПРЕДЕЛЕНИЯ ВОЗРАСТА АККАУНТА ---
def get_account_age(user_id: int) -> str:
    """Приблизительное определение года регистрации по ID"""
    if user_id < 100000000: return "Древний (до 2015)"
    elif user_id < 250000000: return "Около 2016"
    elif user_id < 500000000: return "Около 2017"
    elif user_id < 800000000: return "Около 2018-2019"
    elif user_id < 1500000000: return "Около 2020-2021"
    elif user_id < 5000000000: return "Около 2022-2023"
    elif user_id < 6500000000: return "Свежий (начало 2024)"
    elif user_id < 7500000000: return "Очень свежий (конец 2024 - 2025)"
    else: return "Новорожденный (2026+)"

# --- УТИЛИТЫ ---
def load_data(file, default):
    if not os.path.exists(file): return default
    with open(file, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return default

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- МЕНЮ ---
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡️ Белый список", callback_data="view_whitelist")],
        [InlineKeyboardButton(text="🚫 Список забаненных", callback_data="view_bans")],
        [InlineKeyboardButton(text="👤 Список админов", callback_data="view_admins")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
    ])

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "👋 <b>Доброго времени суток!</b>\n\n"
        "Я бот ⚡️ <b>GROZA</b> ⚡️\n"
        "Борюсь со шлюхоботами и очищаю чаты от спама.\n\n"
        "<i>Для работы мне нужны права администратора в группе.</i>"
    )
    if message.from_user.id in ADMINS:
        await message.answer(text + "\n\n⚙️ <b>Панель админа: /menu</b>", parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@dp.message(Command("menu"), F.from_user.id.in_(ADMINS))
async def cmd_menu(message: Message):
    await message.answer("🛠 <b>Панель управления GROZA</b>", parse_mode="HTML", reply_markup=get_admin_kb())

@dp.callback_query(F.data.startswith("view_"))
async def handle_menu(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    if action == "whitelist":
        data = load_data(DB_FILE, [])
        res = f"📃 <b>Белый список ({len(data)}):</b>\n" + (", ".join(map(str, data[-20:])) if data else "Пусто")
    elif action == "bans":
        data = load_data(BAN_LOG_FILE, [])
        res = f"🚫 <b>История банов (последние 10):</b>\n" + ("\n".join(data[-10:]) if data else "Чисто")
    elif action == "admins":
        res = "👤 <b>Админы:</b>\n" + "\n".join(map(str, ADMINS))
    
    await callback.message.edit_text(res, parse_mode="HTML", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    await callback.message.delete()

@dp.callback_query(F.data.startswith(("admin_whitelist_", "admin_ban_")))
async def process_admin_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return await callback.answer("У тебя нет прав!", show_alert=True)
    
    _, action, user_id, chat_id, msg_id = callback.data.split("_")
    user_id, chat_id, msg_id = int(user_id), int(chat_id), int(msg_id)

    if action == "whitelist":
        whitelist = load_data(DB_FILE, [])
        if user_id not in whitelist:
            whitelist.append(user_id)
            save_data(DB_FILE, whitelist)
            await callback.message.edit_text(callback.message.text + "\n\n✅ <b>Добавлен в исключения</b>", parse_mode="HTML")
        await callback.answer("Готово")

    elif action == "ban":
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            bans = load_data(BAN_LOG_FILE, [])
            bans.append(f"ID: {user_id} (Забанен)")
            save_data(BAN_LOG_FILE, bans)
            await callback.message.edit_text(callback.message.text + "\n\n🚫 <b>АННИГИЛИРОВАН</b>", parse_mode="HTML")
            await callback.answer("Цель уничтожена!")
        except Exception as e:
            await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def monitor(message: Message):
    if not message.text or not message.from_user or message.from_user.is_bot:
        return

    user_id = message.from_user.id
    if user_id in load_data(DB_FILE, []) or user_id in ADMINS:
        return

    if PATTERN.search(message.text):
        stats = load_data(STATS_FILE, {})
        uid_str = str(user_id)
        stats[uid_str] = stats.get(uid_str, 0) + 1
        save_data(STATS_FILE, stats)

        # Вычисляем возраст
        acc_age = get_account_age(user_id)

        chat_id_short = str(message.chat.id).replace("-100", "")
        link = f"https://t.me/c/{chat_id_short}/{message.message_id}"
        if message.chat.username:
            link = f"https://t.me/{message.chat.username}/{message.message_id}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 ЗАБАНИТЬ", callback_data=f"admin_ban_{user_id}_{message.chat.id}_{message.message_id}")],
            [InlineKeyboardButton(text="➕ В исключения", callback_data=f"admin_whitelist_{user_id}_{message.chat.id}_{message.message_id}")]
        ])

        report = (
            f"🚨 <b>ГРОЗА ОБНАРУЖИЛА ЦЕЛЬ</b>\n\n"
            f"📍 <b>Чат:</b> {message.chat.title}\n"
            f"👤 <b>Автор:</b> {message.from_user.full_name} (<code>{user_id}</code>)\n"
            f"📅 <b>Аккаунт:</b> <u>{acc_age}</u>\n"
            f"📊 <b>Актив:</b> {stats[uid_str]} сообщ.\n"
            f"💬 <b>Текст:</b> <i>{message.text[:200]}</i>\n"
            f"🔗 <a href='{link}'>ПЕРЕЙТИ К ЦЕЛИ</a>"
        )

        for admin in ADMINS:
            try:
                await bot.send_message(admin, report, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)
            except: pass

async def main():
    print("ГРОЗА запущена...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
