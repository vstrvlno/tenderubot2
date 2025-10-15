# bot.py
import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

import tender_parser  # импортируем твой parser.py


# --- Настройки ---
TOKEN = os.getenv("BOT_TOKEN")  # токен берётся с Render (из Dashboard → Environment)
PORT = int(os.getenv("PORT", 10000))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 300))  # каждые 5 минут

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment variables!")

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

AWAITING_KEYWORD = {}  # user_id -> "add" или "remove"


# --- Команды ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я TenderuBot — бот для поиска тендеров по ключевым словам.\n\n"
        "Чтобы добавить ключевое слово, набери /addkeyword\n"
        "Чтобы посмотреть список — /listkeywords\n"
        "Чтобы запустить парсинг — /parse"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "/start — запуск бота\n"
        "/help — помощь\n"
        "/about — информация\n"
        "/addkeyword — добавить ключевое слово\n"
        "/removekeyword — удалить ключевое слово\n"
        "/listkeywords — список подписок\n"
        "/parse — принудительно запустить парсер"
    )


@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Что делает бот?", callback_data="about_info")],
        [InlineKeyboardButton(text="Статистика", callback_data="about_stats")]
    ])
    await message.answer("ℹ️ О боте:", reply_markup=kb)


@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    try:
        if data == "about_info":
            await callback.message.answer("🤖 Я нахожу тендеры по площадкам Казахстана и отправляю их по ключевым словам.")
        elif data == "about_stats":
            conn = tender_parser.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tenders")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
            users_row = cur.fetchone()
            users = users_row[0] if users_row else 0
            conn.close()
            await callback.message.answer(f"📊 В базе тендеров: {total}\nПодписчиков: {users}")
        await callback.answer()
    except Exception:
        logging.exception("Ошибка при обработке callback")


@dp.message(Command("addkeyword"))
async def cmd_addkeyword(message: types.Message):
    user_id = message.from_user.id
    AWAITING_KEYWORD[user_id] = "add"
    await message.answer("✍️ Введите ключевое слово, на которое хотите подписаться.")


@dp.message(Command("removekeyword"))
async def cmd_removekeyword(message: types.Message):
    user_id = message.from_user.id
    AWAITING_KEYWORD[user_id] = "remove"
    await message.answer("❌ Введите ключевое слово, которое нужно удалить.")


@dp.message(Command("listkeywords"))
async def cmd_listkeywords(message: types.Message):
    user_id = message.from_user.id
    rows = tender_parser.list_user_keywords(user_id)
    if not rows:
        await message.answer("У вас пока нет подписок.")
    else:
        await message.answer("📚 Ваши ключевые слова:\n" + "\n".join(f"— {r}" for r in rows))


@dp.message(Command("parse"))
async def cmd_parse(message: types.Message):
    await message.answer("🔍 Запрашиваю новые тендеры...")

    try:
        new = await run_parser_once_and_notify()
        await message.answer(f"✅ Готово. Добавлено {len(new)} новых тендеров.")
    except Exception as e:
        logging.exception("Ошибка при парсинге")
        await message.answer(f"⚠️ Ошибка при парсинге: {e}")


# --- Обработка текстов ---
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if user_id in AWAITING_KEYWORD:
        action = AWAITING_KEYWORD.pop(user_id)
        keyword = text.strip()
        if not keyword:
            await message.answer("❌ Ключевое слово пустое, операция отменена.")
            return

        if action == "add":
            tender_parser.add_subscription(user_id, keyword)
            await message.answer(f"✅ Подписка на '{keyword}' добавлена.")
        elif action == "remove":
            tender_parser.remove_subscription(user_id, keyword)
            await message.answer(f"🗑️ Подписка на '{keyword}' удалена (если была).")
        return

    await message.answer("💡 Введите команду /help, чтобы увидеть список доступных команд.")


# --- Запуск парсера ---
async def run_parser_once_and_notify():
    loop = asyncio.get_event_loop()
    tenders = await loop.run_in_executor(None, tender_parser.fetch_tenders, 50)
    added = tenders  # если save_new_tenders не используется, можно возвращать сразу

    if not added:
        logging.info("Новых тендеров нет.")
        return []

    subs = tender_parser.get_subscriptions()
    notifications = {}
    for t in added:
        name = (t.get("name") or "").lower()
        summary = (
            f"📌 {t.get('name')}\n"
            f"Номер: {t.get('purchase_number')}\n"
            f"Заказчик: {t.get('customer')}\n"
            f"Сумма: {t.get('amount')}\n"
            f"Дата: {t.get('publish_date')}"
        )
        for kw, users in subs.items():
            if kw in name:
                for u in users:
                    notifications.setdefault(u, []).append(summary)

    for user_id, msgs in notifications.items():
        try:
            for m in msgs[:10]:
                await bot.send_message(chat_id=user_id, text=m)
            if len(msgs) > 10:
                await bot.send_message(chat_id=user_id, text=f"...и ещё {len(msgs)-10} тендеров.")
        except Exception:
            logging.exception(f"Ошибка при уведомлении пользователя {user_id}")

    logging.info(f"Отправлено уведомлений {len(notifications)} пользователям.")
    return added


# --- Фоновая задача ---
async def polling_task():
    await asyncio.sleep(10)
    while True:
        try:
            logging.info("⏳ Автоматический запуск парсера...")
            await run_parser_once_and_notify()
            logging.info("✅ Парсер завершён, спим...")
        except Exception:
            logging.exception("Ошибка в фоновой задаче парсинга")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# --- Web сервер для Render ---
async def handle_root(request):
    return web.Response(text="TenderuBot is running ✅")


async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"🌐 Web server started on port {PORT}")


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
        logging.info("🛑 Бот остановлен.")



