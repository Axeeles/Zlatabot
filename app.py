import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from dotenv import load_dotenv
import asyncio
import threading
import http.server
import socketserver

# Загружаем .env
load_dotenv()

# Проверка переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN or not CHANNEL_ID or not ADMIN_ID:
    raise ValueError("[ОШИБКА] Не найдены переменные окружения: BOT_TOKEN, CHANNEL_ID, ADMIN_ID")

ADMIN_ID = int(ADMIN_ID)

# Запуск фейкового веб-сервера для Render
def run_server():
    PORT = 10000  # любой свободный порт
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Fake web server running on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# Создаём бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Хранилище статистики
stats = {"users": set()}

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    stats["users"].add(message.from_user.id)
    await message.answer(
        "Привет! 👋\nЯ бот для подписки на канал.\n"
        "Подпишись и получи доступ к контенту!"
    )

@dp.message(F.text == "/stats")
async def stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав на просмотр статистики")
        return
    await message.answer(f"📊 Кол-во пользователей: {len(stats['users'])}")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
