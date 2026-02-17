import asyncio
import json
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ (ПРОВЕРЬ ТОКЕН И ID) ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://mishaswaga.github.io/cvetibot/"
REQUISITES = "💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"
LAT, LON = 55.7558, 37.6173 # Твой адрес на карте

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_promo = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    # Заказы
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, status TEXT)''')
    # Промокоды
    cur.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

# Клавиатуры
def get_admin_kb(o_id, u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🚚 В ПУТИ", callback_data=f"adm_way_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="🏁 ДОСТАВЛЕН", callback_data=f"adm_done_{o_id}_{u_id}")]
    ])

# --- ЛОГИКА ПОЛЬЗОВАТЕЛЯ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="💐 ОТКРЫТЬ МАГАЗИН", web_app=types.WebAppInfo(url=URL))],
        [types.KeyboardButton(text="📜 Мои заказы"), types.KeyboardButton(text="🎁 Бонусы")],
        [types.KeyboardButton(text="📍 Наш адрес")]
    ]
    await message.answer("🌸 **Premium Flower Boutique**\n\nРады вас видеть! Используйте меню ниже:", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
                         parse_mode="Markdown")
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 **Босс, вы в сети.**\nДля добавления промокода: `/addpromo КОД %`")

@dp.message(F.text == "📍 Наш адрес")
async def send_geo(message: types.Message):
    await message.answer_location(LAT, LON)
    await message.answer("🏠 Мы находимся здесь!")

@dp.message(F.text == "📜 Мои заказы")
async def show_history(message: types.Message):
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute("SELECT id, items, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows: return await message.answer("У вас еще нет заказов.")
    res = "📜 **ВАШИ ЗАКАЗЫ:**\n\n"
    for r in rows: res += f"📦 №{r[0]} | {r[1]}\nСтатус: *{r[2]}*\n\n"
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "🎁 Бонусы")
async def show_loyalty(message: types.Message):
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (message.from_user.id,))
    count = cur.fetchone()[0]
    conn.close()
    await message.answer(f"📊 Ваши доставленные заказы: {count}\n\n*Каждый 5-й заказ дает скидку 20%!*")

# --- ПРИЕМ ЗАКАЗА ---

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?, ?, ?, ?)",
                (message.from_user.id, data['items'], data['total'], "NEW"))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()

    admin_text = (
        f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n"
        f"👤 Клиент: @{message.from_user.username or 'без_ника'}\n"
        f"📞 Тел: `{data['phone']}`\n"
        f"📍 Адрес: {data['address']}\n"
        f"⏰ Время: {data['time']}\n"
        f"💐 **СОСТАВ:** {data['items']}\n"
        f"💰 Сумма: **{data['total']}₽**"
    )
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=get_admin_kb(o_id, message.from_user.id), parse_mode="Markdown")
    await message.answer(f"✅ Заказ №{o_id} отправлен! Ждите одобрения.")

# --- УПРАВЛЕНИЕ ЗАКАЗОМ ---

@dp.callback_query(F.data.startswith("adm_"))
async def process_admin_action(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    await state.update_data(o_id=o_id, u_id=u_id, status=status)
    
    # Спрашиваем комментарий (как ты и просил)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Без коммента", callback_data="skip_comment")]])
    await call.message.answer(f"📝 Введите комментарий к заказу №{o_id} (или нажмите пропустить):", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_comment)
    await call.answer()

@dp.message(AdminStates.waiting_for_comment)
async def send_with_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    comment = f"\n\n💬 Комментарий: _{message.text}_"
    await final_status_update(data['o_id'], data['u_id'], data['status'], comment)
    await message.answer("✅ Ответ отправлен клиенту.")
    await state.clear()

@dp.callback_query(F.data == "skip_comment")
async def skip_comment_process(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await final_status_update(data['o_id'], data['u_id'], data['status'], "")
    await call.message.answer("✅ Отправлено без комментария.")
    await state.clear()
    await call.answer()

async def final_status_update(o_id, u_id, status, comment):
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    
    msg = ""
    if status == "yes":
        cur.execute("UPDATE orders SET status = 'ОДОБРЕН' WHERE id = ?", (o_id,))
        msg = f"✅ **ЗАКАЗ №{o_id} ОДОБРЕН!**{comment}\n\nРеквизиты для оплаты:\n`{REQUISITES}`\n\nПришлите чек!"
    elif status == "no":
        cur.execute("UPDATE orders SET status = 'ОТКЛОНЕН' WHERE id = ?", (o_id,))
        msg = f"❌ **ЗАКАЗ №{o_id} ОТКЛОНЕН**{comment}"
    elif status == "way":
        cur.execute("UPDATE orders SET status = 'В ПУТИ' WHERE id = ?", (o_id,))
        msg = f"🚚 **Заказ №{o_id} уже в пути!**"
    elif status == "done":
        cur.execute("UPDATE orders SET status = 'ДОСТАВЛЕН' WHERE id = ?", (o_id,))
        msg = f"🏁 **Заказ №{o_id} доставлен!** Пожалуйста, оцените нашу работу."
        # Проверка лояльности
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (u_id,))
        if cur.fetchone()[0] % 5 == 0:
            await bot.send_message(u_id, "🎁 **ЛОЯЛЬНОСТЬ!** Вы сделали 5-й заказ! Дарим промокод: `LOYALTY20`")
            
    conn.commit()
    conn.close()
    await bot.send_message(u_id, msg, parse_mode="Markdown")

# --- ДОП ФУНКЦИИ ---

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user = message.from_user
    info = f"👤 {user.full_name} (@{user.username or 'нет'})\n🆔 `{user.id}`"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 **ЧЕК!**\n\n{info}", parse_mode="Markdown")
    await message.answer("🙏 Чек получен, проверяем оплату!")

@dp.message(Command("addpromo"))
async def add_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, code, disc = message.text.split()
        conn = sqlite3.connect('flower_business.db')
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO promos VALUES (?, ?)", (code.upper(), int(disc)))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Промокод `{code.upper()}` на {disc}% добавлен!")
    except:
        await message.answer("❌ Ошибка. Пиши: `/addpromo КОД СКИДКА`")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
