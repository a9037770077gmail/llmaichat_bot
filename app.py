import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Получаем токены ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не задан в переменных окружения")

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Обработчики ---
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 Привет! Я AI-помощник на базе Groq. Задавай любые вопросы!")

@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    if not user_text:
        return
    # Здесь вставьте вашу логику обращения к Groq
    # (пока просто эхо для проверки)
    await message.answer(f"Вы спросили: {user_text}")

# --- Flask сервер (для пингов) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускает Flask в отдельном потоке."""
    port = int(os.environ.get("PORT", 5000))
    # debug=False, use_reloader=False обязательны для работы в потоке
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # поток завершится при завершении основного
    flask_thread.start()

    # Запускаем бота в ГЛАВНОМ потоке (так правильно для aiogram)
    logging.info("Запуск polling бота...")
    asyncio.run(dp.start_polling(bot))
