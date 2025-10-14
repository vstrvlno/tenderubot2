# --- Stage 1: Build ---
FROM python:3.12-slim

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Обновляем pip и устанавливаем зависимости
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Экспорт переменных окружения (Render автоматически передает BOT_TOKEN и PORT)
ENV PYTHONUNBUFFERED=1

# --- Stage 2: Run ---
CMD ["python", "bot.py"]
