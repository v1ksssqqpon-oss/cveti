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
    waiting_for_comment = State()
    waiting_for_reqs = State()
    waiting_for_mailing = State()

# --- БД ---
def init_db():
    conn = sqlite3.connect('flower_business.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, items TEXT, total INTEGER, status TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute("INSERT OR IGNORE INTO settings VALUES ('reqs', '💳 Карта Сбер: 0000 0000 0000 0000')")
    conn.commit()
    conn.close()

init_db()

def get_reqs():
    conn = sqlite3.connect('flower_business.db')
    res = conn.execute("SELECT value FROM settings WHERE key = 'reqs'").fetchone()[0]
    conn.close()
    return res

def get_order_kb(o_id, u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"st_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"st_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="📦 Собран", callback_data=f"st_ready_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="🚚 В пути", callback_data=f"st_way_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🏁 Доставлен", callback_data=f"st_done_{o_id}_{u_id}")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    conn = sqlite3.connect('flower_business.db')
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 **Premium Flower Boutique**", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="adm_reqs")],
            [types.InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="adm_mail")],
            [types.InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")]
        ])
        await message.answer("🛠 **ГЛАВНОЕ МЕНЮ АДМИНИСТРАТОРА**", reply_markup=kb)

@dp.callback_query(F.data == "adm_stats")
async def show_stats(call: types.CallbackQuery):
    conn = sqlite3.connect('flower_business.db')
    orders = conn.execute("SELECT COUNT(*), SUM(total) FROM orders WHERE status = 'ДОСТАВЛЕН'").fetchone()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    await call.message.answer(f"📊 **СТАТИСТИКА:**\n\n👥 Клиентов: {users}\n✅ Заказов: {orders[0]}\n💰 Выручка: {orders[1] or 0}₽")
    await call.answer()

@dp.callback_query(F.data == "adm_reqs")
async def change_reqs(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты текстом:")
    await state.set_state(AdminStates.waiting_for_reqs)
    await call.answer()

@dp.message(AdminStates.waiting_for_reqs)
async def save_reqs(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('flower_business.db')
    conn.execute("UPDATE settings SET value = ? WHERE key = 'reqs'", (message.text,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Реквизиты сохранены:\n`{message.text}`", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "adm_mail")
async def start_mail(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📢 Введите текст сообщения для всех клиентов:")
    await state.set_state(AdminStates.waiting_for_mailing)
    await call.answer()

@dp.message(AdminStates.waiting_for_mailing)
async def send_mail(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('flower_business.db')
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], message.text)
            count += 1
        except: pass
    await message.answer(f"✅ Рассылка завершена! Получили {count} человек.")
    await state.clear()

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    o_id = random.randint(1000, 9999)
    conn = sqlite3.connect('flower_business.db')
    conn.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?,?,?,?)", (message.from_user.id, data['items'], data['total'], "NEW"))
    conn.commit()
    conn.close()
    
    admin_msg = (f"🔥 **ЗАКАЗ №{o_id}**\n📍 Способ: **{data['method']}**\n👤 @{message.from_user.username}\n"
                 f"📞 `{data['phone']}`\n🏠 {data['address']}\n💐 {data['items']}\n💰 {data['total']}₽")
    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=get_order_kb(o_id, message.from_user.id), parse_mode="Markdown")
    await message.answer(f"⏳ Заказ №{o_id} принят! Ждите одобрения.")

@dp.callback_query(F.data.startswith("st_"))
async def process_status(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    if status in ["yes", "no"]:
        await state.update_data(o_id=o_id, u_id=u_id, status=status)
        await call.message.answer(f"📝 Комментарий к заказу №{o_id} (или '-'):")
        await state.set_state(AdminStates.waiting_for_comment)
    else:
        st_map = {"ready":"СОБРАН", "way":"В ПУТИ", "done":"ДОСТАВЛЕН"}
        st_text = st_map.get(status)
        conn = sqlite3.connect('flower_business.db')
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (st_text, o_id))
        conn.commit()
        conn.close()
        await bot.send_message(u_id, f"🔔 Статус заказа №{o_id} изменен: **{st_text}**", parse_mode="Markdown")
        if status == "done":
            await bot.send_message(u_id, "🏁 Заказ доставлен! Спасибо! 🌸")
        await call.message.answer(f"✅ Статус {st_text} установлен.")
    await call.answer()

@dp.message(AdminStates.waiting_for_comment)
async def save_comment(message: types.Message, state: FSMContext):
    d = await state.get_data()
    com = "" if message.text == "-" else f"\n\n💬: _{message.text}_"
    if d['status'] == "yes":
        await bot.send_message(d['u_id'], f"✅ **ОДОБРЕН!**{com}\n\nРеквизиты:\n`{get_reqs()}`\n\nЖдем скриншот чека!", parse_mode="Markdown")
    else:
        await bot.send_message(d['u_id'], f"❌ **ОТКЛОНЕН**{com}", parse_mode="Markdown")
    await message.answer("✅ Ответ отправлен клиенту.")
    await state.clear()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 ЧЕК от @{message.from_user.username}")
    await message.answer("🙏 Чек получен, проверяем оплату!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
