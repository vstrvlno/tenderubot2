import logging
import asyncio
import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# === НАСТРОЙКИ ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен из .env
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # твой Telegram ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(level=logging.INFO)

def log_message(user_id, username, text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {username or 'unknown'} (id={user_id}): {text}\n")

# === СОЗДАНИЕ БАЗЫ ДАННЫХ ===
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            joined TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, datetime.now()))
    conn.commit()
    conn.close()

# === КНОПКИ ===
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")],
        [InlineKeyboardButton(text="📞 Поддержка", callback_data="support")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")]
    ])
    return keyboard

# === КОМАНДЫ ===
@dp.message(CommandStart())
async def start_handler(message: Message):
    add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    log_message(message.from_user.id, message.from_user.username, "/start")
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я бот-помощник TenderuBot.\n"
        f"Выбери действие ниже:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def help_handler(message: Message):
    log_message(message.from_user.id, message.from_user.username, "/help")
    await message.answer(
        "🛠 Доступные команды:\n"
        "/start — начать работу с ботом\n"
        "/help — справка\n"
        "/about — информация о проекте\n"
        "/logs — получить логи (только админ)"
    )

@dp.message(Command("about"))
async def about_handler(message: Message):
    log_message(message.from_user.id, message.from_user.username, "/about")
    await message.answer("🤖 TenderuBot — это бот для автоматизации бизнес-процессов и интеграции с сайтами и документами.")

@dp.message(Command("logs"))
async def send_logs(message: Message):
    if message.from_user.id == ADMIN_ID:
        if os.path.exists("logs.txt"):
            await message.answer_document(types.FSInputFile("logs.txt"))
        else:
            await message.answer("Файл логов пока пуст 🕳️")
    else:
        await message.answer("У тебя нет доступа к логам 🚫")

# === ОБРАБОТКА КНОПОК ===
@dp.callback_query(F.data == "about")
async def about_callback(callback: types.CallbackQuery):
    await callback.message.answer("TenderuBot создан для помощи компаниям и интеграции с сайтами и документами 📑")
    await callback.answer()

@dp.callback_query(F.data == "support")
async def support_callback(callback: types.CallbackQuery):
    await callback.message.answer("Связаться с поддержкой можно по адресу: support@tenderu.kz 💬")
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def stats_callback(callback: types.CallbackQuery):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    conn.close()
    await callback.message.answer(f"👥 Всего пользователей: {total_users}")
    await callback.answer()

# === ЭХО ===
@dp.message(F.text)
async def echo_handler(message: Message):
    log_message(message.from_user.id, message.from_user.username, message.text)
    await message.answer(f"Ты написал: {message.text}")

# === СЕРВЕР ДЛЯ RENDER ===
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running ✅")

async def start_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# === ЗАПУСК ===
async def main():
    init_db()
    asyncio.create_task(start_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
