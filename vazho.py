import asyncio
import json
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://mishaswaga.github.io/cvetibot/"
REQUISITES = "💳 Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"

# ТВОИ КООРДИНАТЫ (Для карты)
LATITUDE = 55.7558
LONGITUDE = 37.6173

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS orders 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, 
                    items TEXT, total TEXT, status TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS promos 
                   (code TEXT PRIMARY KEY, discount INTEGER)''')
    # Дефолтный промокод
    cur.execute("INSERT OR IGNORE INTO promos VALUES ('FLOWERS10', 10)")
    conn.commit()
    conn.close()

init_db()

def get_admin_kb(o_id):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"st_yes_{o_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"st_no_{o_id}")],
        [types.InlineKeyboardButton(text="🏁 Доставлен", callback_data=f"st_done_{o_id}")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="💐 МАГАЗИН", web_app=types.WebAppInfo(url=URL))],
        [types.KeyboardButton(text="📍 НАШ АДРЕС"), types.KeyboardButton(text="🎁 МОИ БОНУСЫ")]
    ]
    await message.answer("🌸 Добро пожаловать в Flower Boutique!", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# ФИЧА 5: Геолокация
@dp.message(F.text == "📍 НАШ АДРЕС")
async def send_location(message: types.Message):
    await message.answer_location(LATITUDE, LONGITUDE)
    await message.answer("🏠 Мы находимся здесь! Ждем вас в гости.")

# ФИЧА 1: Лояльность
@dp.message(F.text == "🎁 МОИ БОНУСЫ")
async def check_bonus(message: types.Message):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'DONE'", (message.from_user.id,))
    count = cur.fetchone()[0]
    conn.close()
    await message.answer(f"📊 Ваша активность:\nВыполнено заказов: {count}\n\n*Каждый 5-й заказ дает вам супер-скидку!*", parse_mode="Markdown")

# ФИЧА 4: Генератор промокодов (Команда: /addpromo КЛЮЧ ПРОЦЕНТ)
@dp.message(Command("addpromo"))
async def add_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, code, disc = message.text.split()
        conn = sqlite3.connect('shop.db')
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO promos VALUES (?, ?)", (code.upper(), int(disc)))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Промокод `{code.upper()}` на {disc}% добавлен!", parse_mode="Markdown")
    except:
        await message.answer("❌ Ошибка. Пиши так: `/addpromo ЛЕТО 20`", parse_mode="Markdown")

# Прием заказа
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, username, items, total, status) VALUES (?, ?, ?, ?, ?)",
                (user.id, username, data['items'], data['total'], "NEW"))
    o_id = cur.lastrowid
    conn.commit()
    conn.close()

    admin_text = (
        f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n"
        f"👤 Покупатель: {username}\n"
        f"📞 Тел: `{data['phone']}`\n"
        f"⏰ Время: **{data['time']}**\n"
        f"📍 Адрес: {data['address']}\n"
        f"💐 Заказ: {data['items']}\n"
        f"💰 Итого: **{data['total']}₽**"
    )
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=get_admin_kb(o_id), parse_mode="Markdown")
    await message.answer(f"⏳ Заказ №{o_id} принят! Администратор скоро свяжется с вами.")

# Статусы
@dp.callback_query(F.data.startswith("st_"))
async def change_status(call: types.CallbackQuery):
    _, status, o_id = call.data.split("_")
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM orders WHERE id = ?", (o_id,))
    u_id = cur.fetchone()[0]

    if status == "yes":
        await bot.send_message(u_id, f"✅ **ЗАКАЗ №{o_id} ОДОБРЕН!**\n\nРеквизиты:\n`{REQUISITES}`\n\nЖдем фото чека!")
    elif status == "done":
        cur.execute("UPDATE orders SET status = 'DONE' WHERE id = ?", (o_id,))
        conn.commit()
        await bot.send_message(u_id, f"🏁 **ЗАКАЗ №{o_id} ДОСТАВЛЕН!**\nСпасибо, что выбрали нас!")
        
        # ЛОЯЛЬНОСТЬ: Проверка на каждый 5-й заказ
        cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'DONE'", (u_id,))
        count = cur.fetchone()[0]
        if count % 5 == 0:
            await bot.send_message(u_id, "🎁 **У ВАС ПОДАРОК!**\nЗа вашу преданность дарим промокод `LOYALTY20` на скидку 20%!")
            cur.execute("INSERT OR IGNORE INTO promos VALUES ('LOYALTY20', 20)")
            conn.commit()

    await call.message.answer(f"Статус {status} применен")
    conn.close()
    await call.answer()

@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                         caption=f"🧾 **ЧЕК!**\nОт: @{message.from_user.username or message.from_user.full_name}")
    await message.answer("🙏 Чек получен, проверяем!")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
