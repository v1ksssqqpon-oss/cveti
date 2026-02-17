import asyncio
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_for_reqs = State()

# Хранилище настроек
settings = {
    "requisites": "Карта Сбер: 0000 0000 0000 0000 (Михаил С.)",
    "promos": {"FLOWERS10": 10}
}
orders_db = {}

# --- КЛАВИАТУРЫ ---
def admin_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Изменить реквизиты", callback_data="edit_req")],
        [types.InlineKeyboardButton(text="🎁 Промокоды", callback_data="list_promos")]
    ])

# --- ЛОГИКА АДМИНКИ ---

# Кнопка "Изменить реквизиты"
@dp.callback_query(F.data == "edit_req")
async def edit_req_call(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Введите новые реквизиты для оплаты (номер карты и имя):")
    await state.set_state(AdminStates.waiting_for_reqs)
    await call.answer()

# Сохранение новых реквизитов
@dp.message(AdminStates.waiting_for_reqs)
async def save_reqs(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        settings["requisites"] = message.text
        await message.answer(f"✅ Реквизиты обновлены на:\n`{message.text}`", parse_mode="Markdown", reply_markup=admin_kb())
        await state.clear()

# Просмотр промокодов
@dp.callback_query(F.data == "list_promos")
async def list_promos(call: types.CallbackQuery):
    text = "🎁 **СПИСОК ПРОМОКОДОВ:**\n\n"
    for code, disc in settings["promos"].items():
        text += f"• `{code}` — {disc}%\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

# --- ЛОГИКА ЗАКАЗОВ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 МАГАЗИН ЦВЕТОВ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 Добро пожаловать! Нажмите кнопку ниже для заказа:", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 ПАНЕЛЬ УПРАВЛЕНИЯ:", reply_markup=admin_kb())

# Получение заказа
@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    o_id = random.randint(1000, 9999)
    orders_db[o_id] = {"user_id": message.from_user.id, "data": data}

    # Кнопки Одобрить/Отклонить
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ ОДОБРИТЬ", callback_data=f"order_yes_{o_id}"),
         types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"order_no_{o_id}")]
    ])

    # Формат как на картинке
    admin_text = (
        f"🔥 **НОВЫЙ ЗАКАЗ**\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Тел: `{data['phone']}`\n"
        f"📍 Адрес: {data['address']}\n"
        f"💐 Заказ: {data['items']}\n"
        f"💰 Сумма: {data['total']}₽"
    )
    
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
    await message.answer("⏳ Заказ отправлен флористу. Ждите подтверждения!")

# Кнопки в чате
@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, status, o_id = call.data.split("_")
    order = orders_db.get(int(o_id))
    if not order: return await call.answer("Заказ не найден")

    if status == "yes":
        await bot.send_message(order["user_id"], 
            f"✅ **ВАШ ЗАКАЗ ОДОБРЕН!**\n\nРеквизиты для оплаты:\n`{settings['requisites']}`\n\nОтправьте скриншот чека сюда.")
        # Обновляем сообщение у админа
        await call.message.edit_text(call.message.text + "\n\n✅ **ОДОБРЕНО. Ждем чек.**", parse_mode="Markdown")
    else:
        await bot.send_message(order["user_id"], "❌ Извините, заказ отклонен.")
        await call.message.edit_text(call.message.text + "\n\n❌ ОТКЛОНЕНО.")
    await call.answer()

# ПЕРЕСЫЛКА ЧЕКА (ФОТО) АДМИНУ
@dp.message(F.photo)
async def forward_receipt(message: types.Message):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                         caption=f"🧾 **ПРИШЕЛ ЧЕК ОТ КЛИЕНТА!**\n👤 Юзер: @{message.from_user.username or 'без ника'}\n🆔 ID: `{message.from_user.id}`",
                         parse_mode="Markdown")
    await message.answer("🙏 Спасибо! Чек получен, проверяем оплату.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
