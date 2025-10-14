# Используем стабильный Python 3.11.9
FROM python:3.11.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Загружаем переменные окружения из .env
# (Render автоматически подставит свои Environment Variables)
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "bot.py"]