# Используем официальный Python 3.12
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем все файлы проекта
COPY . .

# Обновляем pip и устанавливаем зависимости
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Экспорт переменных окружения (Render автоматически передает BOT_TOKEN и PORT)
ENV PORT=10000

# Команда запуска бота
CMD ["python", "bot.py"]
