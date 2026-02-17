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
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_new_reqs = State()
    waiting_for_comment = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flower_pro.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, status TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute("INSERT OR IGNORE INTO settings VALUES ('reqs', '💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)')")
    conn.commit()
    conn.close()

init_db()

def get_reqs():
    conn = sqlite3.connect('flower_pro.db')
    res = conn.execute("SELECT value FROM settings WHERE key = 'reqs'").fetchone()[0]
    conn.close()
    return res

def get_admin_kb(o_id, u_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🏁 Доставлен", callback_data=f"adm_done_{o_id}_{u_id}")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 **Premium Flower Boutique**", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        adm_kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="change_reqs")]])
        await message.answer("⚙️ Админ-панель:", reply_markup=adm_kb)

# СМЕНА РЕКВИЗИТОВ
@dp.callback_query(F.data == "change_reqs")
async def start_change_reqs(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты (карту и имя):")
    await state.set_state(AdminStates.waiting_for_new_reqs)
    await call.answer()

@dp.message(AdminStates.waiting_for_new_reqs)
async def save_new_reqs(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('flower_pro.db')
    conn.execute("UPDATE settings SET value = ? WHERE key = 'reqs'", (message.text,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Реквизиты обновлены:\n`{message.text}`", parse_mode="Markdown")
    await state.clear()

# ОБРАБОТКА ЗАКАЗА
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    o_id = random.randint(1000, 9999)
    conn = sqlite3.connect('flower_pro.db')
    conn.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?, ?, ?, ?)", (message.from_user.id, data['items'], data['total'], "NEW"))
    conn.commit()
    conn.close()
    
    admin_msg = (f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n👤 Покупатель: @{message.from_user.username or 'нет'}\n"
                 f"📞 Тел: `{data['phone']}`\n📍 Адрес: {data['address']}\n⏰ Время: {data['time']}\n"
                 f"💐 Заказ: {data['items']}\n💰 Итого: **{data['total']}₽**")
    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=get_admin_kb(o_id, message.from_user.id), parse_mode="Markdown")
    await message.answer(f"⏳ Заказ №{o_id} принят! Ждите одобрения.")

# ОДОБРЕНИЕ И КОММЕНТАРИЙ
@dp.callback_query(F.data.startswith("adm_"))
async def adm_action(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    if status in ["yes", "no"]:
        await state.update_data(o_id=o_id, u_id=u_id, status=status)
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Без комментария", callback_data="skip_com")]])
        await call.message.answer(f"📝 Комментарий к заказу №{o_id}:", reply_markup=kb)
        await state.set_state(AdminStates.waiting_for_comment)
    elif status == "done":
        await bot.send_message(u_id, f"🏁 **Заказ №{o_id} доставлен!** Спасибо!")
        # Лояльность
        conn = sqlite3.connect('flower_pro.db')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'DONE'", (u_id,))
        if cur.fetchone()[0] % 5 == 0: await bot.send_message(u_id, "🎁 Подарок за 5-й заказ! Скидка 20%: `LOYALTY20`")
        conn.close()
    await call.answer()

@dp.message(AdminStates.waiting_for_comment)
async def save_comment(message: types.Message, state: FSMContext):
    d = await state.get_data()
    comment = f"\n\n💬 Комментарий: _{message.text}_"
    await finish_update(d['o_id'], d['u_id'], d['status'], comment)
    await message.answer("✅ Отправлено!")
    await state.clear()

@dp.callback_query(F.data == "skip_com")
async def skip_com(call: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await finish_update(d['o_id'], d['u_id'], d['status'], "")
    await call.message.answer("✅ Отправлено без комм.")
    await state.clear()

async def finish_update(o_id, u_id, status, comment):
    msg = ""
    if status == "yes":
        msg = f"✅ **ЗАКАЗ №{o_id} ОДОБРЕН!**{comment}\n\nРеквизиты:\n`{get_reqs()}`\n\nПришлите чек!"
    else:
        msg = f"❌ **ЗАКАЗ №{o_id} ОТКЛОНЕН**{comment}"
    await bot.send_message(u_id, msg, parse_mode="Markdown")

@dp.message(F.photo)
async def handle_check(message: types.Message):
    caption = f"🧾 **ЧЕК ОБ ОПЛАТЕ**\n👤 От: @{message.from_user.username or 'нет'}\n🆔 ID: `{message.from_user.id}`"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    await message.answer("🙏 Чек получен, проверяем оплату!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
