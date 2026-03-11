import asyncio
import json
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8610106870:AAG1GqHg4IbPIhT-wubEdZ9B1hhTSqp736Q"
ADMIN_ID = 5454985521  # Твой ID, чтобы бот знал, кому слать отчеты
# --------------------

DB_FILE = "whitelist.json"
STATS_FILE = "user_stats.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регулярка для поиска (те же слова)
PATTERN = re.compile(r'(?i)\b(работ[а-я]*|темк[а-я]*|темок|подработ[а-я]*)\b')

# --- Функции работы с базой ---
def load_data(file, default):
    if not os.path.exists(file): return default
    with open(file, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return default

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def monitor(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    user_id = message.from_user.id
    uid_str = str(user_id)

    # 1. Считаем активность
    stats = load_data(STATS_FILE, {})
    stats[uid_str] = stats.get(uid_str, 0) + 1
    save_data(STATS_FILE, stats)

    # 2. Проверяем вайтлист
    whitelist = load_data(DB_FILE, [])
    if user_id in whitelist:
        return

    # 3. Ищем ключевые слова
    if message.text and PATTERN.search(message.text):
        username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
        chat_name = message.chat.title
        
        # Генерируем ссылку на сообщение (если чат публичный)
        link = f"https://t.me/{message.chat.username}/{message.message_id}" if message.chat.username else "Приватный чат"

        report = (
            f"🎯 <b>Нашел работу/темку!</b>\n\n"
            f"📍 <b>Чат:</b> {chat_name}\n"
            f"👤 <b>Автор:</b> {username}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📊 <b>Сообщений в базе:</b> {stats[uid_str]}\n"
            f"💬 <b>Текст:</b> <i>{message.text[:300]}</i>\n\n"
            f"🔗 <a href='{link}'>Перейти к сообщению</a>"
        )

        # Отправка админу
        await bot.send_message(ADMIN_ID, report, parse_mode="HTML", disable_web_page_preview=True)

# --- КОМАНДЫ ДЛЯ АДМИНА ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_to_whitelist(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Используй: /add ID")
    
    try:
        new_id = int(args[1])
        whitelist = load_data(DB_FILE, [])
        if new_id not in whitelist:
            whitelist.append(new_id)
            save_data(DB_FILE, whitelist)
            await message.reply(f"✅ ID {new_id} добавлен в исключения.")
    except ValueError:
        await message.reply("❌ ID должен быть числом.")

# --- ЗАПУСК ---
async def main():
    print("Бот запущен и мониторит группы (aiogram)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
