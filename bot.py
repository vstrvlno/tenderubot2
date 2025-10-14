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
    await message.answer(f"Привет!", {message.from_user.first_name}!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import os
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running")

async def start_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

import asyncio

if __name__ == "__main__":
    from aiogram import executor
    loop = asyncio.get_event_loop()
    loop.create_task(start_server())  # ← открывает порт для Render
    executor.start_polling(dp, skip_updates=True)
