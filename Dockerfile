# --- Используем официальный образ Python ---
FROM python:3.12-slim

# --- Устанавливаем зависимости системы ---
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Создаем рабочую директорию ---
WORKDIR /app

# --- Копируем файлы проекта ---
COPY . /app

# --- Обновляем pip и устанавливаем зависимости ---
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# --- Экспортируем порт (для Render веб-сервера) ---
EXPOSE 10000

# --- Команда для запуска бота ---
CMD ["python", "bot.py"]
