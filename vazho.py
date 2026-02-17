import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = '8380687429:AAFJh0XExc0kBsx2dspQNlmZCUBFO1IFSX0'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_reqs = State()
    waiting_for_comment = State()

db = {"reqs": "Карта Сбер: 0000 0000 0000 0000 (Михаил С.)", "orders": {}}

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 Бот запущен!", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        kb_adm = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="edit_req")]])
        await message.answer("🛠 АДМИНКА:", reply_markup=kb_adm)

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    o_id = random.randint(1000, 9999)
    db["orders"][o_id] = {"user_id": message.from_user.id, "data": data}
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"ord_yes_{o_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"ord_no_{o_id}")]
    ])
    
    text = f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n👤 Имя: {data['name']}\n📞 `{data['phone']}`\n📍 {data['address']}\n💐 {data['items']}\n💰 Сумма: {data['total']}₽"
    await bot.send_message(ADMIN_ID, text, reply_markup=kb, parse_mode="Markdown")
    await message.answer("⏳ Заказ на проверке. Ждите ответа!")

@dp.callback_query(F.data.startswith("ord_"))
async def ask_comment(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id = call.data.split("_")
    await state.update_data(o_id=o_id, status=status)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Без комментария", callback_data="skip_com")]])
    await call.message.answer(f"📝 Введите комментарий к ответу:", reply_markup=kb)
    await state.set_state(States.waiting_for_comment)
    await call.answer()

@dp.message(States.waiting_for_comment)
async def send_res(message: types.Message, state: FSMContext):
    s = await state.get_data()
    order = db["orders"].get(int(s['o_id']))
    com = f"\n\n💬 Коммент: _{message.text}_"
    await finish_ord(order, s['status'], com)
    await message.answer("✅ Отправлено!")
    await state.clear()

@dp.callback_query(F.data == "skip_com")
async def skip_com(call: types.CallbackQuery, state: FSMContext):
    s = await state.get_data()
    order = db["orders"].get(int(s['o_id']))
    await finish_ord(order, s['status'], "")
    await call.message.answer("✅ Отправлено без коммента.")
    await state.clear()
    await call.answer()

async def finish_ord(order, status, com):
    if status == "yes":
        txt = f"✅ **ЗАКАЗ ОДОБРЕН!**{com}\n\nРеквизиты:\n`{db['reqs']}`\n\nЖдем фото чека!"
    else:
        txt = f"❌ **ЗАКАЗ ОТКЛОНЕН**{com}"
    await bot.send_message(order["user_id"], txt, parse_mode="Markdown")

@dp.message(F.photo)
async def get_photo(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption="🧾 **ПРИШЕЛ ЧЕК!**")
    await message.answer("🙏 Чек получен, проверяем!")

@dp.callback_query(F.data == "edit_req")
async def edit_req(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты:")
    await state.set_state(States.waiting_for_reqs)

@dp.message(States.waiting_for_reqs)
async def save_reqs(message: types.Message, state: FSMContext):
    db["reqs"] = message.text
    await message.answer(f"✅ Сохранено: {message.text}")
    await state.clear()

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
