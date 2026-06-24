import os
import asyncio
import threading
import logging
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from groq import Groq

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Получение токенов из переменных окружения ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не задан в переменных окружения")

# --- Инициализация клиента Groq ---
groq_client = Groq(api_key=GROQ_API_KEY)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Обработчик команды /start ---
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 Привет! Я AI-помощник на базе **Groq**.\n"
        "Задавай любой вопрос, и я постараюсь ответить.\n"
        "💡 Чтобы я искал информацию в интернете, добавь в конце сообщения вопросительный знак (?) — но это пока в разработке."
    )

# --- Основной обработчик текстовых сообщений ---
@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    if not user_text:
        return

    # Показываем, что бот "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Вызов Groq
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # можно заменить на mixtral-8x7b-32768 или gemma2-9b-it
            messages=[
                {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке кратко и по делу."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=2048,
        )

        answer = completion.choices[0].message.content
        await message.answer(answer)

    except Exception as e:
        logging.error(f"Ошибка при обращении к Groq: {e}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")

# --- Flask-сервер для пингов (чтобы Render не усыплял бота) ---
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
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота в ГЛАВНОМ потоке (это важно для aiogram)
    logging.info("Запуск polling бота...")
    asyncio.run(dp.start_polling(bot))
