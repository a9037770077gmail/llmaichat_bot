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

# --- НАСТРОЙКА БОТА (скопируйте сюда код вашего бота) ---

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN found in environment variables")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Пример обработчика для команды /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Привет! Я твой AI-помощник на базе Groq!")

# Пример обработчика для текстовых сообщений
@dp.message()
async def echo_message(message: Message):
    user_text = message.text
    # Здесь должна быть логика вашего бота с Groq
    await message.answer(f"Вы написали: {user_text}")

# --- НАСТРОЙКА FLASK ---

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# --- ЗАПУСК БОТА В ОТДЕЛЬНОМ ПОТОКЕ ---

def run_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Запускаем Flask-сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
