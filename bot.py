from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
import parser  # импортируем наш parser.py

# === НАСТРОЙКИ ===
TOKEN = "ВАШ_ТОКЕН_БОТА"
ADMIN_ID = 123456789  # ваш Telegram ID

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаем таблицы при старте
parser.create_tables()

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Отправь /help для списка команд.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "/subscribe <слово> - подписаться на ключевое слово\n"
        "/unsubscribe <слово> - отписаться\n"
        "/list_keywords - список ваших ключевых слов\n"
        "/new_tenders - показать новые тендеры"
    )
    await message.answer(text)

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /subscribe <слово>")
        return
    keyword = args[1].strip()
    parser.add_subscription(message.from_user.id, keyword)
    await message.answer(f"Подписка на '{keyword}' активирована.")

@dp.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /unsubscribe <слово>")
        return
    keyword = args[1].strip()
    parser.remove_subscription(message.from_user.id, keyword)
    await message.answer(f"Подписка на '{keyword}' удалена.")

@dp.message(Command("list_keywords"))
async def cmd_list_keywords(message: Message):
    keywords = parser.get_user_keywords(message.from_user.id)
    if not keywords:
        await message.answer("У вас нет подписок.")
        return
    await message.answer("Ваши ключевые слова: " + ", ".join(keywords))

@dp.message(Command("new_tenders"))
async def cmd_new_tenders(message: Message):
    keywords = parser.get_user_keywords(message.from_user.id)
    if not keywords:
        await message.answer("У вас нет ключевых слов для поиска.")
        return
    texts = []
    for k in keywords:
        tenders = parser.get_tenders_by_keyword(k)
        if tenders:
            for t in tenders:
                texts.append(f"{t[0]}\nЗаказчик: {t[1]}\nСумма: {t[2]}\nДата: {t[3]}\nНомер: {t[4]}\n")
    if not texts:
        await message.answer("Новых тендеров по вашим ключевым словам нет.")
        return
    await message.answer("\n\n".join(texts))

# === ЗАПУСК БОТА ===
if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    asyncio.run(dp.start_polling(bot))
