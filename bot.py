import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

import parser as tender_parser  # parser.py

# --- Загрузка .env ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60*5))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set in .env")

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- State ---
AWAITING_KEYWORD = {}  # user_id -> "add" / "remove"

# --- Команды ---
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я TenderuBot — отправляю тендеры по ключевым словам.\n"
        "Используй /help для списка команд."
    )

@dp.message(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "/start - запустить бота\n"
        "/help - эта справка\n"
        "/about - о боте\n"
        "/addkeyword - добавить ключевое слово\n"
        "/removekeyword - удалить ключевое слово\n"
        "/listkeywords - показать ваши ключевые слова\n"
        "/fetch - принудительно запустить парсер\n"
    )

@dp.message(commands=["about"])
async def cmd_about(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Что делает бот?", callback_data="about_info")],
        [InlineKeyboardButton("Статистика", callback_data="about_stats")]
    ])
    await message.answer("О боте:", reply_markup=kb)

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data or ""
    try:
        if data == "about_info":
            await callback.message.answer("Я нахожу тендеры с goszakup и рассылаю по ключевым словам.")
        elif data == "about_stats":
            conn = tender_parser.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tenders")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
            users_row = cur.fetchone()
            users = users_row[0] if users_row else 0
            conn.close()
            await callback.message.answer(f"Тендеров в базе: {total}\nПодписчиков: {users}")
        await callback.answer()
    except Exception:
        logging.exception("Callback error")

@dp.message(commands=["addkeyword"])
async def cmd_addkeyword(message: types.Message):
    AWAITING_KEYWORD[message.from_user.id] = "add"
    await message.answer("Отправьте ключевое слово для подписки:")

@dp.message(commands=["removekeyword"])
async def cmd_removekeyword(message: types.Message):
    AWAITING_KEYWORD[message.from_user.id] = "remove"
    await message.answer("Отправьте ключевое слово для удаления:")

@dp.message(commands=["listkeywords"])
async def cmd_listkeywords(message: types.Message):
    rows = tender_parser.list_user_keywords(message.from_user.id)
    if not rows:
        await message.answer("У вас нет подписок.")
    else:
        await message.answer("Ваши ключевые слова:\n" + "\n".join(f"- {r}" for r in rows))

@dp.message(commands=["fetch"])
async def cmd_fetch(message: types.Message):
    await message.answer("Запускаю парсер...")
    new = await run_parser_once_and_notify()
    await message.answer(f"Готово. Добавлено {len(new)} новых тендеров.")

# --- Обработка обычного текста ---
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    if user_id in AWAITING_KEYWORD:
        action = AWAITING_KEYWORD.pop(user_id)
        keyword = message.text.strip()
        if not keyword:
            await message.answer("Ключевое слово пустое. Отмена.")
            return
        if action == "add":
            tender_parser.add_subscription(user_id, keyword)
            await message.answer(f"✅ Подписка на '{keyword}' добавлена.")
        else:
            tender_parser.remove_subscription(user_id, keyword)
            await message.answer(f"✅ Подписка на '{keyword}' удалена.")
    else:
        await message.answer("Я принимаю команды. Введите /help для списка команд.")

# --- Парсер + уведомления ---
async def run_parser_once_and_notify():
    loop = asyncio.get_event_loop()
    tenders = await loop.run_in_executor(None, tender_parser.fetch_tenders, 50)
    added = await loop.run_in_executor(None, tender_parser.save_new_tenders, tenders)

    if not added:
        logging.info("No new tenders.")
        return []

    subs = await loop.run_in_executor(None, tender_parser.get_subscriptions)
    notifications = {}
    for t in added:
        name = (t.get("name") or "").lower()
        msg = f"📌 {t.get('name')}\nНомер: {t.get('purchase_number')}\nЗаказчик: {t.get('customer')}\nСумма: {t.get('amount')}\nДата: {t.get('publish_date')}"
        for kw, users in subs.items():
            if kw in name:
                for u in users:
                    notifications.setdefault(u, []).append(msg)

    for user_id, msgs in notifications.items():
        try:
            for m in msgs[:10]:
                await bot.send_message(chat_id=user_id, text=m)
            if len(msgs) > 10:
                await bot.send_message(chat_id=user_id, text=f"...и ещё {len(msgs)-10} тендеров.")
        except Exception:
            logging.exception(f"Notify user {user_id} failed.")

    logging.info(f"Sent notifications to {len(notifications)} users.")
    return added

# --- Фоновый polling ---
async def polling_task():
    await asyncio.sleep(5)
    while True:
        try:
            logging.info("Periodic parser run started")
            await run_parser_once_and_notify()
            logging.info("Periodic parser run finished")
        except Exception:
            logging.exception("Error in periodic parser")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

# --- Webserver для Render ---
async def handle_root(request):
    return web.Response(text="TenderuBot is running")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Web server started on port {PORT}")

# --- Main ---
async def main():
    tender_parser.create_tables()
    await asyncio.gather(
        start_webserver(),
        polling_task(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down...")
        try:
            asyncio.run(bot.session.close())
        except Exception:
            pass
