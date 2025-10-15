from aiogram import Router, types
from tender_parser import save_new_tenders, get_tenders_from_site  # твои функции
import logging

router = Router()

@router.message(commands=["parse"])
async def cmd_parse(message: types.Message):
    await message.answer("Запрашиваю новые тендеры...")
    logging.info(f"User {message.from_user.id} вызвал /parse")
    
    from config import SITES

    total_added = 0
    for site in SITES:
        try:
            tenders = await get_tenders_from_site(site)
            added = save_new_tenders(tenders)
            total_added += len(added)
            await message.answer(f"✅ {site['name']}: найдено {len(tenders)}, добавлено {len(added)}")
            logging.info(f"{site['name']}: найдено {len(tenders)}, добавлено {len(added)}")
        except Exception as e:
            await message.answer(f"❌ Ошибка при обработке {site['name']}: {e}")
            logging.exception(f"Ошибка при парсинге {site['name']}")

    await message.answer(f"Готово! Всего добавлено новых тендеров: {total_added}")
