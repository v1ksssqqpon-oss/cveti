import asyncio
import json
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
APP_URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS promos 
                   (code TEXT PRIMARY KEY, discount INTEGER)''')
    # Добавим тестовый промокод
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

class AdminStates(StatesGroup):
    waiting_for_promo = State()
    waiting_for_broadcast = State()

# --- КЛАВИАТУРЫ ---
def get_admin_kb():
    kb = [
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
         types.InlineKeyboardButton(text="🎁 Промокоды", callback_data="manage_promos")],
        [types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
        [types.InlineKeyboardButton(text="🛒 Заказы (Последние 5)", callback_data="recent_orders")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

# --- ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 ОТКРЫТЬ МАГАЗИН", web_app=types.WebAppInfo(url=APP_URL))]]
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Добро пожаловать, Босс! Магазин готов.", 
                             reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await message.answer("⚙️ ПАНЕЛЬ УПРАВЛЕНИЯ:", reply_markup=get_admin_kb())
    else:
        await message.answer("🌸 Привет! Выбирай лучшие цветы в нашем приложении:", 
                             reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("⚙️ ПАНЕЛЬ УПРАВЛЕНИЯ:", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(total) FROM orders")
    count, total = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM orders")
    users = cur.fetchone()[0]
    conn.close()
    
    text = (f"📈 **ОТЧЕТ ПО ПРОДАЖАМ**\n\n"
            f"✅ Всего заказов: {count or 0}\n"
            f"💰 Общая выручка: {total or 0}₽\n"
            f"👥 Уникальных клиентов: {users or 0}")
    await callback.message.edit_text(text, reply_markup=get_admin_kb())

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    # Сохраняем в базу
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total) VALUES (?, ?, ?)", 
                (message.from_user.id, data['items'], data['total']))
    conn.commit()
    conn.close()

    # Уведомление админу
    await bot.send_message(ADMIN_ID, f"🔥 **НОВЫЙ ЗАКАЗ!**\n\n👤 {data['name']}\n📞 {data['phone']}\n💐 {data['items']}\n💰 Сумма: {data['total']}₽\n📍 {data['address']}")
    await message.answer("✨ Заказ принят! Мы уже начали собирать ваш букет.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
