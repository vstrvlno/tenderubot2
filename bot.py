import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from parser import parse_data  # Импорт функции парсера

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Переменная TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Бот запущен ✅")

# Команда /parse - запускает парсер
@dp.message(Command("parse"))
async def parse_handler(message: Message):
    await message.answer("Начинаю парсинг данных...")
    try:
        data = parse_data()  # вызываем функцию из parser.py
        await message.answer(f"Данные успешно получены:\n{data}")
    except Exception as e:
        await message.answer(f"Ошибка при парсинге: {e}")

# Echo-хендлер для проверки сообщений
@dp.message()
async def echo_handler(message: Message):
    await message.answer(f"Ты написал: {message.text}")

# Запуск бота
async def main():
    try:
        print("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
