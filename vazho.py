import asyncio
import json
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ (ПРОВЕРЬ СВОИ ДАННЫЕ) ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

# Твои реквизиты (можно менять через код или текстом в базе)
DEFAULT_REQS = "💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для диалогов
class Form(StatesGroup):
    waiting_for_comment = State()
    waiting_for_reqs = State()
    waiting_for_review = State()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('flower_shop.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, 
                    items TEXT, total INTEGER, status TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS promos 
                   (code TEXT PRIMARY KEY, discount INTEGER)''')
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

# Клавиатура для админа (управление заказом)
def get_admin_kb(o_id, u_id):
    kb = [
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"ans_yes_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"ans_no_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="📦 СОБРАН", callback_data=f"st_ready_{o_id}_{u_id}"),
         types.InlineKeyboardButton(text="🚚 В ПУТИ", callback_data=f"st_way_{o_id}_{u_id}")],
        [types.InlineKeyboardButton(text="🏁 ДОСТАВЛЕН", callback_data=f"st_done_{o_id}_{u_id}")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРАБОТКА КОМАНД ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))],
        [types.KeyboardButton(text="📜 МОИ ЗАКАЗЫ"), types.KeyboardButton(text="📍 АДРЕС")]
    ]
    await message.answer("🌸 **Добро пожаловать в наш цветочный бутик!**\n\nИспользуйте меню для заказа или проверки статуса.", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
                         parse_mode="Markdown")
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **Вы зашли как администратор.**\nДля добавления промокода: `/addpromo КОД %`", parse_mode="Markdown")

@dp.message(F.text == "📍 АДРЕС")
async def send_geo(message: types.Message):
    await message.answer_location(55.7558, 37.6173) # Укажи свои координаты
    await message.answer("🏠 Мы ждем вас по адресу: ул. Цветочная, д. 1")

@dp.message(F.text == "📜 МОИ ЗАКАЗЫ")
async def show_history(message: types.Message):
    conn = sqlite3.connect('flower_shop.db')
    cur = conn.cursor()
    cur.execute("SELECT id, items, total, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return await message.answer("У вас пока нет заказов. Время это исправить! 💐")
    
    text = "📜 **ВАШИ ПОСЛЕДНИЕ ЗАКАЗЫ:**\n\n"
    for r in rows:
        text += f"🔹 Заказ №{r[0]}: {r[1]}\n💰 Сумма: {r[2]}₽\nСтатус: *{r[3]}*\n\n"
    await message.answer(text, parse_mode="Markdown")

# --- ПРИЕМ ЗАКАЗА ---

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    # Сохраняем в БД
    conn = sqlite3.connect('flower_shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, username, items, total, status) VALUES (?, ?, ?, ?, ?)",
                (user.id, username, data['items'], data['total'], "ОЖИДАЕТ"))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Уведомление Админу
    admin_text = (
        f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n"
        f"👤 Клиент: {username}\n"
        f"📞 Тел: `{data['phone']}`\n"
        f"📍 Адрес: {data['address']}\n"
        f"⏰ Время: {data['time']}\n\n"
        f"💐 **СОСТАВ:**\n{data['items']}\n\n"
        f"💰 Итого: **{data['total']}₽**"
    )
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=get_admin_kb(o_id, user.id), parse_mode="Markdown")
    await message.answer(f"✅ **Заказ №{o_id} принят!**\nМы проверяем наличие цветов и скоро пришлем подтверждение.")

# --- АДМИНКА: ОДОБРЕНИЕ И КОММЕНТАРИИ ---

@dp.callback_query(F.data.startswith("ans_"))
async def step_one_answer(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id, u_id = call.data.split("_")
    await state.update_data(cur_o=o_id, cur_u=u_id, cur_status=status)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Без комментария", callback_data="skip_com")]])
    word = "ОДОБРЕНИЮ" if status == "yes" else "ОТКЛОНЕНИЮ"
    await call.message.answer(f"📝 Введите комментарий к {word} заказа №{o_id}:", reply_markup=kb)
    await state.set_state(Form.waiting_for_comment)
    await call.answer()

@dp.message(Form.waiting_for_comment)
async def save_comment_and_send(message: types.Message, state: FSMContext):
    s = await state.get_data()
    comment = f"\n\n💬 Комментарий: _{message.text}_"
    await finish_order(s['cur_o'], s['cur_u'], s['cur_status'], comment)
    await message.answer("✅ Ответ отправлен покупателю!")
    await state.clear()

@dp.callback_query(F.data == "skip_com")
async def skip_comment_callback(call: types.CallbackQuery, state: FSMContext):
    s = await state.get_data()
    await finish_order(s['cur_o'], s['cur_u'], s['cur_status'], "")
    await call.message.answer("✅ Отправлено без комментария.")
    await state.clear()
    await call.answer()

async def finish_order(o_id, u_id, status, comment):
    conn = sqlite3.connect('flower_shop.db')
    cur = conn.cursor()
    if status == "yes":
        new_status = "ОДОБРЕН"
        text = f"✅ **ВАШ ЗАКАЗ №{o_id} ОДОБРЕН!**{comment}\n\nРеквизиты для оплаты:\n`{DEFAULT_REQS}`\n\nПришлите скриншот чека в этот чат."
    else:
        new_status = "ОТКЛОНЕН"
        text = f"❌ **ЗАКАЗ №{o_id} ОТКЛОНЕН**{comment}"
    
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, o_id))
    conn.commit()
    conn.close()
    await bot.send_message(u_id, text, parse_mode="Markdown")

# --- СТАТУСЫ И ЛОЯЛЬНОСТЬ ---

@dp.callback_query(F.data.startswith("st_"))
async def update_status(call: types.CallbackQuery):
    _, status, o_id, u_id = call.data.split("_")
    status_map = {"ready": "СОБРАН", "way": "В ПУТИ", "done": "ДОСТАВЛЕН"}
    new_st = status_map.get(status)
    
    if not new_st: return await call.answer()

    conn = sqlite3.connect('flower_shop.db')
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (new_st, o_id))
    conn.commit()

    await bot.send_message(u_id, f"🔔 **Статус заказа №{o_id} изменен:**\nТеперь он: *{new_st}*", parse_mode="Markdown")
    
    if status == "done":
        # Лояльность: каждый 5-й заказ
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'ДОСТАВЛЕН'", (u_id,))
        count = cur.fetchone()[0]
        if count % 5 == 0:
            await bot.send_message(u_id, "🎁 **У НАС ПОДАРОК!**\nВы сделали уже 5 заказов! Дарим вам промокод `LOYALTY20` на скидку 20%!")

    conn.close()
    await call.answer(f"Статус: {new_st}")

# --- ФОТО ЧЕКА ---

@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    user = message.from_user
    info = f"👤 {user.full_name} (@{user.username if user.username else 'нет_ника'})\n🆔 ID: `{user.id}`"
    
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                         caption=f"🧾 **ПРИШЕЛ ЧЕК ОБ ОПЛАТЕ!**\n\n{info}", parse_mode="Markdown")
    await message.answer("🙏 **Спасибо!**\nЧек получен, проверяем оплату. Мы сообщим, когда начнем сборку.")

# --- ПРОМОКОДЫ ---

@dp.message(Command("addpromo"))
async def add_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, code, disc = message.text.split()
        conn = sqlite3.connect('flower_shop.db')
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO promos VALUES (?, ?)", (code.upper(), int(disc)))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Промокод `{code.upper()}` на {disc}% успешно добавлен!")
    except:
        await message.answer("❌ Ошибка! Пиши так: `/addpromo ВЕСНА 15`")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
