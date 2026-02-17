import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = '8380687429:AAFJh0XExc0kBsx2dspQNlmZCUBFO1IFSX0'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_reqs = State()
    waiting_for_comment = State() # Для комментов к заказу

settings = {"requisites": "Карта Сбер: 0000 0000 0000 0000 (Михаил С.)"}
orders_db = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 Магазин открыт!", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        kb_admin = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="edit_req")]])
        await message.answer("🛠 АДМИН-ПАНЕЛЬ:", reply_markup=kb_admin)

# Прием заказа
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    o_id = random.randint(1000, 9999)
    orders_db[o_id] = {"user_id": message.from_user.id, "data": data}

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"ans_yes_{o_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"ans_no_{o_id}")]
    ])
    
    admin_text = f"🔥 **НОВЫЙ ЗАКАЗ №{o_id}**\n\n👤 Имя: {data['name']}\n📞 `{data['phone']}`\n📍 {data['address']}\n💐 {data['items']}\n💰 Сумма: {data['total']}₽"
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    await message.answer("⏳ Заказ на проверке. Ожидайте сообщения!")

# Клик по кнопке (Одобрить/Отклонить)
@dp.callback_query(F.data.startswith("ans_"))
async def ask_comment(call: types.CallbackQuery, state: FSMContext):
    _, status, o_id = call.data.split("_")
    await state.update_data(current_order=o_id, current_status=status)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_comment")]])
    action = "ОДОБРЕНИЮ" if status == "yes" else "ОТКЛОНЕНИЮ"
    await call.message.answer(f"📝 Введите комментарий к **{action}** заказа (или нажмите пропустить):", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_comment)
    await call.answer()

# Сохранение комментария и отправка клиенту
@dp.message(AdminStates.waiting_for_comment)
async def send_final_res(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    order = orders_db.get(int(data_state['current_order']))
    comment = f"\n\n💬 Комментарий: _{message.text}_" if message.text else ""
    
    await finish_order_process(order, data_state['current_status'], comment)
    await message.answer("✅ Ответ отправлен клиенту!")
    await state.clear()

@dp.callback_query(F.data == "skip_comment")
async def skip_comment(call: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    order = orders_db.get(int(data_state['current_order']))
    await finish_order_process(order, data_state['current_status'], "")
    await call.message.answer("✅ Отправлено без комментария.")
    await state.clear()
    await call.answer()

async def finish_order_process(order, status, comment):
    if status == "yes":
        msg = f"✅ **ВАШ ЗАКАЗ ОДОБРЕН!**{comment}\n\nРеквизиты:\n`{settings['requisites']}`\n\nЖдем скриншот чека!"
    else:
        msg = f"❌ **ЗАКАЗ ОТКЛОНЕН**{comment}\n\nСвяжитесь с нами для уточнения."
    await bot.send_message(order["user_id"], msg, parse_mode="Markdown")

# Пересылка чека
@dp.message(F.photo)
async def forward_receipt(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption="🧾 **ПРИШЕЛ ЧЕК!**", parse_mode="Markdown")
    await message.answer("🙏 Спасибо! Чек получен.")

# Смена реквизитов
@dp.callback_query(F.data == "edit_req")
async def edit_req(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты:")
    await state.set_state(AdminStates.waiting_for_reqs)

@dp.message(AdminStates.waiting_for_reqs)
async def save_reqs(message: types.Message, state: FSMContext):
    settings["requisites"] = message.text
    await message.answer(f"✅ Сохранено: {message.text}")
    await state.clear()

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
