import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище в памяти
orders_db = {} 
settings = {
    "requisites": "Карта Сбер: 0000 0000 0000 0000 (Михаил С.)",
    "promos": {"FLOWERS10": 10, "BRO": 50}
}

# Клавиатура Админа
def admin_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="edit_req")],
        [types.InlineKeyboardButton(text="🎁 Список промокодов", callback_data="list_promos")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 Магазин готов к работе!", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 ПАНЕЛЬ УПРАВЛЕНИЯ:", reply_markup=admin_kb())

# Прием заказа из Mini App
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    order_id = random.randint(1000, 9999)
    orders_db[order_id] = {"user_id": message.from_user.id, "data": data}

    # Кнопки для тебя
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"order_yes_{order_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"order_no_{order_id}")]
    ])

    admin_text = (f"📦 **ЗАКАЗ №{order_id}**\n\n👤 Имя: {data['name']}\n📞 `{data['phone']}`\n📍 {data['address']}\n"
                  f"💐 {data['items']}\n💰 Итого: **{data['total']}₽**")
    
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    await message.answer("⏳ Заказ отправлен на проверку флористу. Ожидайте подтверждения!")

# Обработка Одобрения/Отклонения
@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    action, status, o_id = call.data.split("_")
    order = orders_db.get(int(o_id))
    if not order: return await call.answer("Заказ устарел")

    if status == "yes":
        await bot.send_message(order["user_id"], 
            f"✅ **ВАШ ЗАКАЗ ОДОБРЕН!**\n\nДля оплаты переведите сумму на реквизиты:\n`{settings['requisites']}`\n\nПосле оплаты пришлите скриншот чека сюда.")
        await call.message.edit_text(call.message.text + "\n\n🟢 ОДОБРЕНО. Реквизиты отправлены.")
    else:
        await bot.send_message(order["user_id"], "❌ К сожалению, мы не можем принять ваш заказ сейчас.")
        await call.message.edit_text(call.message.text + "\n\n🔴 ОТКЛОНЕНО.")
    await call.answer()

# Просмотр промокодов
@dp.callback_query(F.data == "list_promos")
async def list_promos(call: types.CallbackQuery):
    text = "🎁 **ДЕЙСТВУЮЩИЕ ПРОМОКОДЫ:**\n\n"
    for code, disc in settings["promos"].items():
        text += f"• `{code}` — {disc}%\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
