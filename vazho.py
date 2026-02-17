import asyncio
import json
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = '8387192018:AAG_yJ0JEwX0v_lsF8pVkSA74ZpqaaHR5Jo'
ADMIN_ID = 1655167987 
URL = "https://mishaswaga.github.io/cvetibot/"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flowers.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total TEXT, 
                    status TEXT, name TEXT, phone TEXT, address TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS reviews 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, rating INTEGER, text TEXT)''')
    conn.commit()
    conn.close()

init_db()

class States(StatesGroup):
    waiting_for_reqs = State()
    waiting_for_comment = State()
    waiting_for_review = State()

# --- КЛАВИАТУРЫ ---
def get_order_kb(o_id):
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
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 Добро пожаловать!\n/history — мои заказы\n/start — открыть магазин", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(Command("history"))
async def history(message: types.Message):
    conn = sqlite3.connect('flowers.db')
    cur = conn.cursor()
    cur.execute("SELECT id, items, total, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    
    if not rows: return await message.answer("У вас пока нет заказов.")
    
    res = "📜 **ВАША ИСТОРИЯ ЗАКАЗОВ:**\n\n"
    for r in rows:
        res += f"🔹 Заказ №{r[0]}: {r[1]}\n💰 Сумма: {r[2]}₽\nСтатус: *{r[3]}*\n\n"
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    conn = sqlite3.connect('flowers.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total, status, name, phone, address) VALUES (?,?,?,?,?,?,?)",
                (message.from_user.id, data['items'], data['total'], "Ожидает проверки", data['name'], data['phone'], data['address']))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()

    text = f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n👤 Имя: {data['name']}\n📞 `{data['phone']}`\n💐 {data['items']}\n💰 Итого: {data['total']}₽"
    await bot.send_message(ADMIN_ID, text, reply_markup=get_order_kb(o_id), parse_mode="Markdown")
    await message.answer(f"⏳ Заказ №{o_id} принят! Статус можно проверить через /history")

@dp.callback_query(F.data.startswith("st_"))
async def change_status(call: types.CallbackQuery):
    _, status, o_id = call.data.split("_")
    status_map = {"yes": "Одобрен", "no": "Отклонен", "ready": "Собран", "way": "В пути", "done": "Доставлен"}
    new_status = status_map[status]
    
    conn = sqlite3.connect('flowers.db')
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, o_id))
    cur.execute("SELECT user_id FROM orders WHERE id = ?", (o_id,))
    u_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    await bot.send_message(u_id, f"🔔 **Статус заказа №{o_id} изменен:**\nТеперь он: *{new_status}*", parse_mode="Markdown")
    
    if status == "done":
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rev_{o_id}")]])
        await bot.send_message(u_id, "🌸 Букет доставлен! Будем рады вашему отзыву:", reply_markup=kb)
    
    await call.answer(f"Статус: {new_status}")

# --- ОТЗЫВЫ ---
@dp.callback_query(F.data.startswith("rev_"))
async def start_review(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Оцените нашу работу от 1 до 5 (просто напишите цифру и ваш комментарий):")
    await state.set_state(States.waiting_for_review)
    await call.answer()

@dp.message(States.waiting_for_review)
async def save_review(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, f"🌟 **НОВЫЙ ОТЗЫВ!**\nОт: @{message.from_user.username}\nТекст: {message.text}")
    await message.answer("🙏 Спасибо за ваш отзыв! Мы станем еще лучше.")
    await state.clear()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                         caption=f"🧾 **ЧЕК!**\n👤 {message.from_user.full_name}\n🔗 @{message.from_user.username}")
    await message.answer("✅ Чек передан администратору.")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
