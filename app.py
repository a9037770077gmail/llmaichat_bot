import os
import asyncio
import threading
import logging
import aiohttp
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Получение токенов из переменных окружения ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не задан в переменных окружения")

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Конфигурация OpenRouter ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Модель по умолчанию — можно заменить на любую другую из каталога OpenRouter
DEFAULT_MODEL = "google/gemini-2.5-flash"  # или "openai/gpt-4o", "anthropic/claude-3.5-sonnet" и т.д.
YOUR_SITE_URL = os.environ.get("SITE_URL", "https://t.me/ваш_канал")  # для статистики OpenRouter
YOUR_APP_NAME = os.environ.get("APP_NAME", "Telegram AI Bot")

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

    # Показываем, что бот "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Формируем запрос к OpenRouter
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": YOUR_SITE_URL,  # Для статистики OpenRouter
                "X-Title": YOUR_APP_NAME,       # Имя вашего приложения
            }
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке кратко и по делу."},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
            }

            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logging.error(f"OpenRouter ошибка {response.status}: {error_text}")
                    await message.answer(f"⚠️ Ошибка API: {response.status}. Попробуйте позже.")
                    return

                data = await response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "Извините, не удалось получить ответ.")
                await message.answer(answer)

    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenRouter: {e}")
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
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота в ГЛАВНОМ потоке
    logging.info("Запуск polling бота с OpenRouter...")
    asyncio.run(dp.start_polling(bot))
