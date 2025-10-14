import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


@dp.message()
async def echo(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}!")


# --- HTTP-сервер для Render (чтобы контейнер не падал) ---
async def handle(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


# --- Основной запуск ---
async def main():
    # запускаем веб-сервер и бота параллельно
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    asyncio.run(main())
