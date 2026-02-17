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
REQUISITES = "💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для комментов
class Form(StatesGroup):
    waiting_for_comment = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flower_empire.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, status TEXT)''')
    cur.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

# Клавиатура управления для тебя
def get_admin_kb(o_id, u_id):
    kb = [
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"adm_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"adm_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🚚 В ПУТИ", callback_data=f"adm_way_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="🏁 ДОСТАВЛЕН", callback_data=f"adm_done_{o_id}_{u_id}")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="💐 ОТКРЫТЬ МАГАЗИН", web_app=types.WebAppInfo(url=URL))],
        [types.KeyboardButton(text="📜 Мои заказы"), types.KeyboardButton(text="📍 Наш адрес")]
    ]
    await message.answer("🌸 **Premium Flower Boutique**\n\nРады тебя видеть! Жми на кнопку, чтобы выбрать лучшие букеты.", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
                         parse_mode="Markdown")
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **Панель Босса активна.**\nДобавить промокод: `/addpromo КОД %`", parse_mode="Markdown")

@dp.message(F.text == "📍 Наш адрес")
async def send_geo(message: types.Message):
    await message.answer_location(55.7558, 37.6173) # Твои координаты
    await message.answer("🏠 Мы находимся здесь! Приходите за свежими цветами.")

@dp.message(F.text == "📜 Мои заказы")
async def show_history(message: types.Message):
    conn = sqlite3.connect('flower_empire.db')
    cur = conn.cursor()
    cur.execute("SELECT id, items, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows: return await message.answer("У тебя пока нет заказов. Исправим? 💐")
    res = "📜 **ТВОИ ПОСЛЕДНИЕ ЗАКАЗЫ:**\n\n"
    for r in rows: res += f"📦 Заказ №{r[0]}\n💐 {r[1]}\nСтатус: *{r[2]}*\n\n"
    await message.answer(res, parse_mode="Markdown")

# --- ПРИЕМ ЗАКАЗА ---

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    conn = sqlite3.connect('flower_empire.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, items, total, status) VALUES (?, ?, ?, ?)",
                (message.from_user.id, data['items'], data['total'], "НОВЫЙ"))
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
        f"💰 Итого: **{data['total']}₽**"
    )
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=get_admin_kb(o_id, message.from_user.id), parse_mode="Markdown")
    await message.answer(f"✅ Заказ №{o_id} отправлен флористу! Жди подтверждения в этом чате.")

# --- АДМИНКА И СТАТУСЫ ---

@dp.callback_query(F.data.startswith("adm_"))
async def admin_action(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    await state.update_data(o_id=o_id, u_id=u_id, status=status)
    
    # Если нажал Одобрить/Отклонить — просим коммент
    if status in ["yes", "no"]:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Без комментария", callback_data="skip_comment")]])
        await call.message.answer(f"📝 Введи комментарий для клиента по заказу №{o_id}:", reply_markup=kb)
        await state.set_state(Form.waiting_for_comment)
    else:
        # Для "В пути" и "Доставлен" коммент не просим, шлем сразу
        await final_update(o_id, u_id, status, "")
        await call.message.answer(f"✅ Статус {status} обновлен.")
    await call.answer()

@dp.message(Form.waiting_for_comment)
async def save_comment(message: types.Message, state: FSMContext):
    d = await state.get_data()
    comment = f"\n\n💬 Комментарий: _{message.text}_"
    await final_update(d['o_id'], d['u_id'], d['status'], comment)
    await message.answer("✅ Ответ с комментарием отправлен.")
    await state.clear()

@dp.callback_query(F.data == "skip_comment")
async def skip_comment(call: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await final_update(d['o_id'], d['u_id'], d['status'], "")
    await call.message.answer("✅ Отправлено без комментария.")
    await state.clear()
    await call.answer()

async def final_update(o_id, u_id, status, comment):
    conn = sqlite3.connect('flower_empire.db')
    cur = conn.cursor()
    msg = ""
    
    if status == "yes":
        cur.execute("UPDATE orders SET status = 'ОДОБРЕН' WHERE id = ?", (o_id,))
        msg = f"✅ **ТВОЙ ЗАКАЗ №{o_id} ОДОБРЕН!**{comment}\n\nРеквизиты для оплаты:\n`{REQUISITES}`\n\nСкинь скрин чека сюда!"
    elif status == "no":
        cur.execute("UPDATE orders SET status = 'ОТКЛОНЕН' WHERE id = ?", (o_id,))
        msg = f"❌ **ЗАКАЗ №{o_id} ОТКЛОНЕН**{comment}"
    elif status == "way":
        cur.execute("UPDATE orders SET status = 'В ПУТИ' WHERE id = ?", (o_id,))
        msg = f"🚚 **Заказ №{o_id} уже в пути!** Скоро будем."
    elif status == "done":
        cur.execute("UPDATE orders SET status = 'ДОСТАВЛЕН' WHERE id = ?", (o_id,))
        msg = f"🏁 **Заказ №{o_id} доставлен!** Спасибо, что доверяешь нам."
        # Проверка лояльности (5-й заказ)
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (u_id,))
        if cur.fetchone()[0] % 5 == 0:
            await bot.send_message(u_id, "🎁 **У НАС ПОДАРОК!** Ты сделал 5 заказов! Твой промокод на -20%: `LOYALTY20`")
            
    conn.commit()
    conn.close()
    await bot.send_message(u_id, msg, parse_mode="Markdown")

# --- ДОПЫ ---

@dp.message(F.photo)
async def get_check(message: types.Message):
    user = message.from_user
    info = f"👤 {user.full_name} (@{user.username or 'нет'})\n🆔 `{user.id}`"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 **ПРИШЕЛ ЧЕК!**\n\n{info}", parse_mode="Markdown")
    await message.answer("🙏 Чек получил, проверяем оплату!")

@dp.message(Command("addpromo"))
async def add_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, code, disc = message.text.split()
        conn = sqlite3.connect('flower_empire.db')
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO promos VALUES (?, ?)", (code.upper(), int(disc)))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Промокод `{code.upper()}` на {disc}% добавлен!")
    except:
        await message.answer("❌ Ошибка. Пиши: `/addpromo КОД %` (Например: /addpromo BRO 20)")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
