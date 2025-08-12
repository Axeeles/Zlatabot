import os
import json
import asyncio
import threading
import http.server
import socketserver
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from dotenv import load_dotenv

# ==== Загрузка переменных окружения ====
if os.path.exists(".env"):
    load_dotenv()
    print("[INFO] Файл .env загружен")
else:
    print("[INFO] Файл .env не найден, берём переменные из окружения системы")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")
ARTICLE_URL = os.getenv("ARTICLE_URL", "https://example.com")  # ссылка на статью

missing_vars = []
if not BOT_TOKEN:
    missing_vars.append("BOT_TOKEN")
if not CHANNEL_ID:
    missing_vars.append("CHANNEL_ID")
if not ADMIN_ID:
    missing_vars.append("ADMIN_ID")

if missing_vars:
    raise ValueError(f"[ОШИБКА] Не найдены переменные окружения: {', '.join(missing_vars)}")

ADMIN_ID = int(ADMIN_ID)

# ==== Фейковый веб-сервер для Render ====
def run_server():
    PORT = 10000
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[INFO] Fake web server running on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ==== Создаём бота ====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==== Хранилище статистики ====
stats_file = "stats.json"
stats = {"users": {}}

def save_stats():
    try:
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats["users"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Ошибка сохранения статистики: {e}")

# Загрузка и автоконвертация старого формата
if os.path.exists(stats_file):
    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        save_needed = False
        if isinstance(loaded_data, list):
            print("[INFO] Найден старый формат статистики, выполняю конвертацию...")
            today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stats["users"] = {
                str(uid): {"first_seen": today, "last_seen": today}
                for uid in loaded_data
            }
            save_needed = True
        elif isinstance(loaded_data, dict):
            stats["users"] = loaded_data
        else:
            print("[WARN] stats.json имеет неизвестный формат, начинаем с пустой статистики")

        print(f"[INFO] Загружено пользователей: {len(stats['users'])}")

        if save_needed:
            save_stats()
            print("[INFO] Конвертация завершена, файл stats.json обновлён")

    except Exception as e:
        print(f"[ERROR] Ошибка загрузки статистики: {e}")

def update_user_stats(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if str(user_id) not in stats["users"]:
        stats["users"][str(user_id)] = {"first_seen": today, "last_seen": today}
    else:
        stats["users"][str(user_id)]["last_seen"] = today
    save_stats()

# ==== Проверка подписки ====
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"[ERROR] Ошибка проверки подписки: {e}")
        return False

# ==== Хэндлеры ====
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    update_user_stats(message.from_user.id)

    # Отправляем первую фотку с приветствием
    photo = FSInputFile("zlatapic.jpg")
    await message.answer_photo(
        photo,
        caption=(
            "Приветик! Статья уже ждёт тебя! 💡\n"
            "Бот высылает моментально, поэтому жду только твою подписку.\n"
            "ENTER с любовью, kammmil💋"
        )
    )

    if await is_subscribed(message.from_user.id):
        await send_article_ready(message.chat.id)
    else:
        await ask_to_subscribe(message.chat.id)

async def ask_to_subscribe(chat_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="check_subscribe")]
    ])
    await bot.send_message(chat_id, "Не вижу твоей подписки", reply_markup=kb)

async def send_article_ready(chat_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статья", url=ARTICLE_URL)]
    ])
    photo = FSInputFile("zlatapic1.jpg")
    await bot.send_photo(
        chat_id,
        photo,
        caption="Отлично! Благодарю за подписку🤍",
        reply_markup=kb
    )

# ==== Обработка кнопок ====
@dp.callback_query(F.data == "check_subscribe")
async def check_subscribe_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        try:
            await callback.message.delete()  # удаляем сообщение с кнопкой
        except:
            pass
        await send_article_ready(callback.from_user.id)
    else:
        await ask_to_subscribe(callback.from_user.id)
    await callback.answer()

# ==== /stats ====
@dp.message(F.text == "/stats")
async def stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав на просмотр статистики")
        return
    
    total_users = len(stats["users"])
    last_users = list(stats["users"].items())[-10:]  # последние 10
    
    text = f"📊 Всего пользователей: {total_users}\n\nПоследние 10:\n"
    for uid, dates in last_users:
        if isinstance(dates, dict):
            first_seen = dates.get("first_seen", "неизвестно")
            last_seen = dates.get("last_seen", "неизвестно")
        else:
            first_seen = last_seen = "неизвестно"

        # Получаем имя пользователя
        try:
            chat = await bot.get_chat(int(uid))
            name = chat.full_name
        except:
            name = "Без имени"
        
        text += f"👤 {name} (ID: {uid}) | первый визит: {first_seen} | последний визит: {last_seen}\n"

    await message.answer(text)

# ==== /debug ====
@dp.message(F.text == "/debug")
async def debug_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав для этой команды")
        return
    
    await message.answer(
        f"<b>BOT_TOKEN:</b> {BOT_TOKEN if BOT_TOKEN else '❌ Не найден'}\n"
        f"<b>CHANNEL_ID:</b> {CHANNEL_ID if CHANNEL_ID else '❌ Не найден'}\n"
        f"<b>ADMIN_ID:</b> {ADMIN_ID if ADMIN_ID else '❌ Не найден'}\n"
        f"<b>ARTICLE_URL:</b> {ARTICLE_URL}"
    )

# ==== Запуск бота ====
async def main():
    print("[INFO] Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
