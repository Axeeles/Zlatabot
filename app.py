import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# Загружаем переменные окружения (.env для локального теста, Render использует Environment Variables)
load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ARTICLE_URL = os.getenv("ARTICLE_URL")

if not TOKEN or not CHANNEL_ID or not ARTICLE_URL:
    raise ValueError("❌ Не найдены переменные окружения: TOKEN, CHANNEL_ID или ARTICLE_URL.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка базы данных
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        user_id INTEGER PRIMARY KEY,
        last_sent TIMESTAMP,
        sent_count INTEGER DEFAULT 0
    )
""")
conn.commit()

# Кнопки
continue_button = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Продолжить", callback_data="check_subscription")]]
)

article_button = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Статья", url=ARTICLE_URL)]]
)

async def is_subscribed(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    caption = (
        "Привет! Статья уже ждет тебя! Бот высылает моментально, "
        "поэтому жду только твою подписку💡\n\n"
        "с любовью, kammmil 💋"
    )
    await message.answer_photo(
        photo=types.FSInputFile("zlatapic.jpg"),
        caption=caption,
        reply_markup=continue_button
    )

    if await is_subscribed(message.from_user.id):
        await send_article(message.from_user.id)

@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await send_article(callback.from_user.id)
    else:
        await callback.message.answer("Зайчик, не вижу твоей подписочки 🐇")

async def send_article(user_id: int):
    await bot.send_message(user_id, "Отлично! благодарю за подписку🤍")
    await bot.send_photo(
        user_id,
        photo=types.FSInputFile("zlatapic1.jpg"),
        reply_markup=article_button
    )

    # Запись в БД для напоминаний
    cursor.execute(
        "INSERT OR REPLACE INTO reminders (user_id, last_sent, sent_count) VALUES (?, ?, ?)",
        (user_id, datetime.now().isoformat(), 0)
    )
    conn.commit()

async def reminders():
    """Фоновая задача для напоминаний"""
    while True:
        await asyncio.sleep(60)  # проверка каждую минуту
        now = datetime.now()
        cursor.execute("SELECT user_id, last_sent, sent_count FROM reminders")
        for user_id, last_sent, sent_count in cursor.fetchall():
            if sent_count >= 3:
                continue
            last_time = datetime.fromisoformat(last_sent)
            delay = timedelta(days=3) if sent_count > 0 else timedelta(minutes=15)
            if now - last_time >= delay:
                try:
                    await bot.send_message(user_id, "Не забывай про статью 📖")
                    cursor.execute(
                        "UPDATE reminders SET last_sent = ?, sent_count = sent_count + 1 WHERE user_id = ?",
                        (now.isoformat(), user_id)
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Ошибка отправки напоминания: {e}")

async def main():
    asyncio.create_task(reminders())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())