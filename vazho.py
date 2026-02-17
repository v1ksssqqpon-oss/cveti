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

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_reqs = State()
    waiting_for_comment = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, status TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute("INSERT OR IGNORE INTO settings VALUES ('reqs', '💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)')")
    conn.commit()
    conn.close()

init_db()

def get_reqs():
    conn = sqlite3.connect('flower_business.db')
    res = conn.execute("SELECT value FROM settings WHERE key = 'reqs'").fetchone()[0]
    conn.close()
    return res

# Клавиатуры
def admin_main_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Сменить реквизиты", callback_data="change_reqs")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

def get_order_kb(o_id, u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"ans_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"ans_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🚚 В ПУТИ", callback_data=f"ans_way_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="🏁 ДОСТАВЛЕН", callback_data=f"ans_done_{o_id}_{u_id}")]
    ])

# --- ЛОГИКА ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН", web_app=types.WebAppInfo(url=URL))],
          [types.KeyboardButton(text="📜 Мои заказы")]]
    await message.answer("🌸 **Добро пожаловать в Flower Boutique!**", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Админ-панель:", reply_markup=admin_main_kb())

@dp.message(F.text == "📜 Мои заказы")
async def history(message: types.Message):
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute("SELECT id, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows: return await message.answer("У вас нет заказов.")
    text = "📜 **ИСТОРИЯ ЗАКАЗОВ:**\n\n" + "\n".join([f"📦 №{r[0]} | Статус: {r[1]}" for r in rows])
    await message.answer(text)

# Смена реквизитов
@dp.callback_query(F.data == "change_reqs")
async def cmd_change_reqs(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты (карта и имя):")
    await state.set_state(AdminStates.waiting_for_reqs)
    await call.answer()

@dp.message(AdminStates.waiting_for_reqs)
async def save_reqs(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('flower_business.db')
    conn.execute("UPDATE settings SET value = ? WHERE key = 'reqs'", (message.text,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Новые реквизиты сохранены:\n`{message.text}`", parse_mode="Markdown")
    await state.clear()

# Прием заказа
@dp.message(F.web_app_data)
async def handle_webapp(message: types.Message):
    data = json.loads(message.web_app_data.data)
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?, ?, ?, ?)",
                (message.from_user.id, data['items'], data['total'], "НОВЫЙ"))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    admin_msg = (f"🔥 **ЗАКАЗ №{o_id}**\n👤 @{message.from_user.username}\n📞 `{data['phone']}`\n"
                 f"📍 {data['address']}\n⏰ {data['time']}\n💐 {data['items']}\n💰 **{data['total']}₽**")
    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=get_order_kb(o_id, message.from_user.id), parse_mode="Markdown")
    await message.answer(f"✅ Заказ №{o_id} принят! Ожидайте подтверждения.")

# Статусы
@dp.callback_query(F.data.startswith("ans_"))
async def process_ans(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    await state.update_data(o_id=o_id, u_id=u_id, status=status)
    
    if status in ["yes", "no"]:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_com")]])
        await call.message.answer(f"📝 Комментарий к заказу №{o_id}:", reply_markup=kb)
        await state.set_state(AdminStates.waiting_for_comment)
    else:
        await finish_update(o_id, u_id, status, "")
        await call.message.answer("✅ Статус обновлен")
    await call.answer()

@dp.message(AdminStates.waiting_for_comment)
async def save_comment(message: types.Message, state: FSMContext):
    d = await state.get_data()
    await finish_update(d['o_id'], d['u_id'], d['status'], f"\n💬: {message.text}")
    await message.answer("✅ Отправлено")
    await state.clear()

@dp.callback_query(F.data == "skip_com")
async def skip_comment(call: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await finish_update(d['o_id'], d['u_id'], d['status'], "")
    await call.message.answer("✅ Отправлено без комм.")
    await state.clear()

async def finish_update(o_id, u_id, status, comment):
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    msg = ""
    if status == "yes":
        msg = f"✅ **ЗАКАЗ ОДОБРЕН!**{comment}\n\nРеквизиты:\n`{get_reqs()}`\nПришлите чек!"
        cur.execute("UPDATE orders SET status = 'ОДОБРЕН' WHERE id = ?", (o_id,))
    elif status == "way":
        msg = "🚚 **Букет уже в пути!**"
        cur.execute("UPDATE orders SET status = 'В ПУТИ' WHERE id = ?", (o_id,))
    elif status == "done":
        msg = "🏁 **Доставлен!** Спасибо!"
        cur.execute("UPDATE orders SET status = 'ДОСТАВЛЕН' WHERE id = ?", (o_id,))
        # Лояльность
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (u_id,))
        if cur.fetchone()[0] % 5 == 0: await bot.send_message(u_id, "🎁 Подарок! Скидка 20% на 5-й заказ: `LOYALTY20`")
    elif status == "no":
        msg = f"❌ **ОТКЛОНЕН**{comment}"
        cur.execute("UPDATE orders SET status = 'ОТКЛОНЕН' WHERE id = ?", (o_id,))
    
    conn.commit()
    conn.close()
    await bot.send_message(u_id, msg, parse_mode="Markdown")

@dp.message(F.photo)
async def handle_check(message: types.Message):
    info = f"👤 {message.from_user.full_name} (@{message.from_user.username})\n🆔 `{message.from_user.id}`"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 **ЧЕК!**\n\n{info}")
    await message.answer("🙏 Чек получен, проверяем!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
