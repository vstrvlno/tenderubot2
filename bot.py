import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

@dp.message()
async def echo(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())