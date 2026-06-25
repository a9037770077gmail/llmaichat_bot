import os
import asyncio
import threading
import logging
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import httpx

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

# --- Функция для запроса к OpenRouter ---
async def ask_openrouter(prompt: str) -> str:
    """Отправляет запрос к OpenRouter и возвращает ответ."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Опционально: если хотите видеть свои запросы в логах OpenRouter
        "HTTP-Referer": "https://t.me/your_bot_username",
        "X-Title": "AI Chat Bot"
    }
    # Можно выбрать любую бесплатную модель из списка OpenRouter
    # Например: "google/gemini-2.5-flash", "meta-llama/llama-3.3-70b-instruct", "mistralai/mistral-7b-instruct:free"
    data = {
        "model": "google/gemini-2.5-flash",  # или "meta-llama/llama-3.3-70b-instruct"
        "messages": [
            {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке кратко и по делу."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=data, headers=headers)
        if response.status_code != 200:
            logging.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            raise Exception(f"API error {response.status_code}: {response.text}")
        result = response.json()
        return result["choices"][0]["message"]["content"]

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
        answer = await ask_openrouter(user_text)
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"⚠️ Ошибка API: {e}. Попробуйте позже.")

# --- Flask-сервер для пингов ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    logging.info("Запуск polling бота...")
    asyncio.run(dp.start_polling(bot))
