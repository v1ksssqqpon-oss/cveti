import asyncio
import json
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://mishaswaga.github.io/cvetibot/"
REQUISITES = "💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"
LAT, LON = 55.7558, 37.6173 # Твои координаты

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    add_name = State()
    add_price = State()
    waiting_for_review = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, items TEXT, total INTEGER, status TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, disc INTEGER)')
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

# --- КЛАВИАТУРЫ ---
def get_admin_kb(o_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"st_yes_{o_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"st_no_{o_id}")],
        [types.InlineKeyboardButton(text="📦 Собран", callback_data=f"st_ready_{o_id}"),
         types.InlineKeyboardButton(text="🚚 В пути", callback_data=f"st_way_{o_id}")],
        [types.InlineKeyboardButton(text="🏁 Доставлен", callback_data=f"st_done_{o_id}")]
    ])

# --- ЛОГИКА ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="💐 МАГАЗИН", web_app=types.WebAppInfo(url=URL))],
        [types.KeyboardButton(text="📍 Наш адрес"), types.KeyboardButton(text="📜 Мои заказы")]
    ]
    await message.answer("🌸 Добро пожаловать!", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        adm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_p"),
             types.InlineKeyboardButton(text="🗑 Удалить товар", callback_data="del_p")]
        ])
        await message.answer("🛠 АДМИН-ПАНЕЛЬ:", reply_markup=adm_kb)

@dp.message(F.text == "📍 Наш адрес")
async def send_geo(message: types.Message):
    await message.answer_location(LAT, LON)

@dp.message(F.text == "📜 Мои заказы")
async def show_history(message: types.Message):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT id, items, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows: return await message.answer("У вас еще нет заказов.")
    text = "📜 **ВАШИ ЗАКАЗЫ:**\n\n"
    for r in rows: text += f"Заказ №{r[0]}: {r[1]}\nСтатус: {r[2]}\n\n"
    await message.answer(text, parse_mode="Markdown")

# Обработка заказа
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?, ?, ?, ?)",
                (message.from_user.id, data['items'], data['total'], "NEW"))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()

    text = f"🔥 **ЗАКАЗ №{o_id}**\n👤 {data['name']}\n📞 `{data['phone']}`\n⏰ {data['time']}\n💐 {data['items']}\n💰 {data['total']}₽"
    await bot.send_message(ADMIN_ID, text, reply_markup=get_admin_kb(o_id), parse_mode="Markdown")
    await message.answer(f"✅ Заказ №{o_id} принят!")

# СТАТУСЫ И ЛОЯЛЬНОСТЬ
@dp.callback_query(F.data.startswith("st_"))
async def set_status(call: types.CallbackQuery):
    _, status, o_id = call.data.split("_")
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM orders WHERE id = ?", (o_id,))
    u_id = cur.fetchone()[0]

    st_map = {"yes": "ОДОБРЕН", "ready": "СОБРАН", "way": "В ПУТИ", "done": "ДОСТАВЛЕН", "no": "ОТКЛОНЕН"}
    new_st = st_map[status]
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_st, o_id))
    conn.commit()

    if status == "yes":
        await bot.send_message(u_id, f"✅ Заказ №{o_id} одобрен!\nРеквизиты:\n`{REQUISITES}`\nПришлите чек!")
    elif status == "done":
        await bot.send_message(u_id, "🏁 Заказ доставлен! Пожалуйста, оставьте отзыв.")
        # Лояльность
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (u_id,))
        if cur.fetchone()[0] % 5 == 0:
            await bot.send_message(u_id, "🎁 Подарок! Скидка 20% на следующий заказ: `LOYALTY20`")
    else:
        await bot.send_message(u_id, f"🔔 Статус заказа №{o_id}: {new_st}")

    await call.message.answer(f"Статус {new_st} установлен")
    conn.close()
    await call.answer()

@dp.message(F.photo)
async def get_photo(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 ЧЕК от @{message.from_user.username}")
    await message.answer("🙏 Чек получен!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
