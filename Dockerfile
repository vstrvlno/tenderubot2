# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Экспортируем порт для Render
EXPOSE 10000

# Команда запуска бота
CMD ["python", "bot.py"]
