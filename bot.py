# bot.py
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

import parser as tender_parser  # наш parser.py (в том же каталоге)

# Загружаем .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60 * 5))  # 5 минут по умолчанию

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set in .env")

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Для простого "state" (когда пользователь отправляет ключевое слово после /addkeyword)
AWAITING_KEYWORD = {}  # user_id -> action: "add" или "remove"

# --- Хелперы для DB (используем функции из parser.py) ---
# tender_parser.create_tables() создаёт таблицы

# --- Команды ---
@dp.message()
async def handle_message(message: types.Message):
    text = (message.text or "").strip()
    user_id = message.from_user.id

    # Если юзер в режиме добавления/удаления ключевого слова
    if user_id in AWAITING_KEYWORD:
        action = AWAITING_KEYWORD.pop(user_id)
        keyword = text.strip()
        if not keyword:
            await message.answer("Ключевое слово пустое. Отмена.")
            return

        if action == "add":
            tender_parser.add_subscription(user_id, keyword)
            await message.answer(f"✅ Подписка на '{keyword}' добавлена.")
        elif action == "remove":
            tender_parser.remove_subscription(user_id, keyword)
            await message.answer(f"✅ Подписка на '{keyword}' удалена (если была).")
        return

    # Прямой текст — можно обработать как запрос поиска
    await message.answer("Я принимаю команды. Набери /help чтобы увидеть список команд.")


@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я TenderuBot — отправляю тендеры по ключевым словам.\n\n"
        "Команды: /help"
    )

@dp.message(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "/start - запустить бота\n"
        "/help - эта справка\n"
        "/about - о боте\n"
        "/addkeyword - добавить ключевое слово (на которое вы подпишетесь)\n"
        "/removekeyword - удалить ключевое слово\n"
        "/listkeywords - показать ваши ключевые слова\n"
        "/fetch - принудительно запустить парсер (только вы)\n"
    )

@dp.message(commands=["about"])
async def cmd_about(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Что делает бот?", callback_data="about_info")],
        [InlineKeyboardButton(text="Статистика", callback_data="about_stats")]
    ])
    await message.answer("О боте:", reply_markup=kb)

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data or ""
    try:
        if data == "about_info":
            await callback.message.answer("Я нахожу тендеры с goszakup и рассылаю по ключевым словам.")
        elif data == "about_stats":
            # простая статистика
            conn = tender_parser.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tenders")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
            users = cur.fetchone()[0] if cur.fetchone() is not None else None
            conn.close()
            await callback.message.answer(f"Тендеров в базе: {total}")
        else:
            await callback.message.answer("Неизвестная кнопка.")
        # всегда безопасно пытаться ответить callback; если слишком поздно — поймаем исключение
        try:
            await callback.answer()
        except Exception as e:
            logging.warning(f"Callback answer failed (probably too old): {e}")
    except Exception as e:
        logging.exception("Error handling callback")

@dp.message(commands=["addkeyword"])
async def cmd_addkeyword(message: types.Message):
    user_id = message.from_user.id
    AWAITING_KEYWORD[user_id] = "add"
    await message.answer("Отправьте ключевое слово (одно слово или фразу) — я подпишу вас на него.")

@dp.message(commands=["removekeyword"])
async def cmd_removekeyword(message: types.Message):
    user_id = message.from_user.id
    AWAITING_KEYWORD[user_id] = "remove"
    await message.answer("Отправьте ключевое слово которое хотите удалить из подписок.")

@dp.message(commands=["listkeywords"])
async def cmd_listkeywords(message: types.Message):
    user_id = message.from_user.id
    rows = tender_parser.list_user_keywords(user_id)
    if not rows:
        await message.answer("У вас нет подписок.")
    else:
        await message.answer("Ваши ключевые слова:\n" + "\n".join(f"- {r}" for r in rows))

@dp.message(commands=["fetch"])
async def cmd_fetch(message: types.Message):
    # привилегия: любой может запустить, но это ручной триггер
    await message.answer("Запрашиваю новые тендеры...")
    new = await run_parser_once_and_notify()
    await message.answer(f"Готово. Добавлено {len(new)} новых тендеров.")

# --- Парсер + уведомление ---
async def run_parser_once_and_notify():
    """
    Запустит парсер, сохранит новые тендеры, сопоставит их с подписками и отправит сообщения.
    Возвращает список добавленных tender dicts.
    """
    # fetch & save
    loop = asyncio.get_event_loop()
    tenders = await loop.run_in_executor(None, tender_parser.fetch_tenders, 50)
    added = await loop.run_in_executor(None, tender_parser.save_new_tenders, tenders)  # список словарей

    if not added:
        logging.info("No new tenders to process.")
        return []

    # подгружаем подписки
    subs = await loop.run_in_executor(None, tender_parser.get_subscriptions)  # dict keyword -> set(user_id)
    # нормализуем ключевые слова
    # пробегаем по новым тендерам и проверяем наличие ключевых слов
    notifications = {}  # user_id -> list of messages
    for t in added:
        name = (t.get("name") or "").lower()
        summary = f"📌 {t.get('name')}\nНомер: {t.get('purchase_number')}\nЗаказчик: {t.get('customer')}\nСумма: {t.get('amount')}\nДата: {t.get('publish_date')}"
        for kw, users in subs.items():
            if kw and kw.lower() in name:
                for u in users:
                    notifications.setdefault(u, []).append(summary)

    # отправляем уведомления (по пользователям)
    for user_id, msgs in notifications.items():
        # склеим в одно сообщение (ограничение размера — простая реализация)
        try:
            for m in msgs[:10]:  # не шлём больше 10 тендеров за раз
                await bot.send_message(chat_id=user_id, text=m)
            if len(msgs) > 10:
                await bot.send_message(chat_id=user_id, text=f"...и ещё {len(msgs)-10} тендеров.")
        except Exception:
            logging.exception(f"Failed to notify user {user_id}")

    logging.info(f"Notifications sent to {len(notifications)} users.")
    return added

# --- Фоновая задача: периодический polling парсера ---
async def polling_task():
    await asyncio.sleep(5)  # даём сервису подняться
    while True:
        try:
            logging.info("Periodic parser run started")
            await run_parser_once_and_notify()
            logging.info("Periodic parser run finished")
        except Exception:
            logging.exception("Error in periodic parser run")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

# --- HTTP-сервер (для Render) ---
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

# --- main ---
async def main():
    # ensure DB tables
    tender_parser.create_tables()

    # запускаем веб-сервер + polling background + бот
    await asyncio.gather(
        start_webserver(),
        polling_task(),
        dp.start_polling(bot, allowed_updates=types.AllowedUpdates.all())
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
