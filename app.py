import asyncio
import os
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = "@kammmil7"
ARTICLE_URL = "https://teletype.in/@kammm_il/yoWPlRbSYae"

if not TOKEN:
    raise ValueError("❌ TOKEN не найден! Проверь .env или переменные окружения.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных для напоминаний
conn = sqlite3.connect("reminders.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    user_id INTEGER,
    next_time TEXT,
    count INTEGER
)
""")
conn.commit()


def set_reminder(user_id):
    now = datetime.now()
    cur.execute("SELECT count FROM reminders WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        count = row[0]
        if count >= 3:
            return
        next_time = now + timedelta(days=3)
        cur.execute("UPDATE reminders SET next_time = ?, count = ? WHERE user_id = ?",
                    (next_time.isoformat(), count + 1, user_id))
    else:
        first_time = now + timedelta(minutes=15)
        cur.execute("INSERT INTO reminders (user_id, next_time, count) VALUES (?, ?, ?)",
                    (user_id, first_time.isoformat(), 0))
    conn.commit()


async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print("Ошибка проверки подписки:", e)
        return False


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    caption = (
        "Привет! Статья уже ждет тебя! Бот высылает моментально, "
        "поэтому жду только твою подписку💡\n\n"
        "с любовью, kammmil 💋"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="check_sub")]
    ])

    await message.answer_photo(
        photo=types.FSInputFile("zlatapic.jpg"),
        caption=caption,
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data == "check_sub")
async def callback_check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if await check_subscription(user_id):
        set_reminder(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Статья", url=ARTICLE_URL)]
        ])
        await callback_query.message.answer_photo(
            photo=types.FSInputFile("zlatapic1.jpg"),
            caption="Отлично! благодарю за подписку🤍",
            reply_markup=keyboard
        )
    else:
        await callback_query.message.answer("Зайчик, не вижу твоей подписочки")


async def reminder_loop():
    while True:
        now = datetime.now()
        cur.execute("SELECT user_id, next_time, count FROM reminders")
        for user_id, next_time, count in cur.fetchall():
            if count < 3 and datetime.fromisoformat(next_time) <= now:
                try:
                    await bot.send_message(user_id, "Не забывай про статью")
                    new_time = now + timedelta(days=3)
                    cur.execute("UPDATE reminders SET next_time = ?, count = ? WHERE user_id = ?",
                                (new_time.isoformat(), count + 1, user_id))
                    conn.commit()
                except Exception as e:
                    print(f"Ошибка отправки напоминания {user_id}: {e}")
        await asyncio.sleep(60)


async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())