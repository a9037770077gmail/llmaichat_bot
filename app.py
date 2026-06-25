import os
import asyncio
import threading
import logging
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from groq import Groq
from openai import OpenAI  # для OpenRouter (совместим с OpenAI API)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Получение токенов из переменных окружения ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не задан в переменных окружения")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не задан в переменных окружения")

# --- Инициализация клиентов ---
# OpenRouter (через OpenAI-совместимый клиент)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Обработчик команды /start ---
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 Привет! Я AI-помощник, подключённый к **OpenRouter**.\n"
        "Я могу использовать разные модели: Gemini, GPT, Claude и другие.\n"
        "💡 Напиши любой вопрос, и я постараюсь ответить!"
    )

# --- Основной обработчик текстовых сообщений ---
@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    if not user_text:
        return

    # Показываем "печатает..."
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Пытаемся через OpenRouter
        completion = openrouter_client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",  # можно сменить на другую модель
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
        error_str = str(e)
        logging.error(f"OpenRouter API error: {e}")

        # Если ошибка 403 (лимит превышен) или "Key limit exceeded"
        if "403" in error_str or "Key limit exceeded" in error_str:
            # Переключаемся на Groq (fallback)
            try:
                await message.answer("🔄 Лимит OpenRouter исчерпан, переключаюсь на Groq...")

                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке кратко и по делу."},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.7,
                    max_tokens=2048,
                )
                answer = completion.choices[0].message.content
                await message.answer(answer)

            except Exception as groq_error:
                logging.error(f"Groq fallback error: {groq_error}")
                await message.answer(
                    "⚠️ **Все API временно недоступны.**\n"
                    "Пожалуйста, попробуйте позже."
                )

        else:
            # Другие ошибки
            await message.answer(
                "⚠️ **Произошла ошибка при обращении к API.**\n"
                "Попробуйте позже или сообщите администратору."
            )

# --- Flask-сервер для пингов (чтобы Render не усыплял бота) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускает Flask в отдельном потоке."""
    port = int(os.environ.get("PORT", 5000))
    # debug=False, use_reloader=False обязательны для работы в потоке
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота в ГЛАВНОМ потоке (это важно для aiogram)
    logging.info("Запуск polling бота...")
    asyncio.run(dp.start_polling(bot))
