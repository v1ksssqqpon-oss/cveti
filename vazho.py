import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- ТВОИ КОНФИГИ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
MY_ID = 1655167987 
APP_URL = 'https://v1ksssqqpon-oss.github.io/cveti/' 

# Реквизиты для оплаты (поменяй на свои)
PAYMENT_DETAILS = "💳 Карта: `2200 0000 0000 0000` (Сбербанк)\n👤 Получатель: Иван И."

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатура для админа
def get_admin_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить и ждать оплату", callback_data=f"accept_{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="🌸 ВЫБРАТЬ БУКЕТ", web_app=WebAppInfo(url=APP_URL))]]
    await message.answer(
        f"Привет, {message.from_user.first_name}! 💐\nВыбирай цветы, а мы доставим их вовремя.",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    await message.answer("⏳ **Заказ отправлен!**\nДождитесь подтверждения от флориста.")

    admin_msg = (
        f"🔥 **НОВЫЙ ЗАКАЗ**\n\n"
        f"👤 **Имя:** {data['name']}\n"
        f"📞 **Тел:** `{data['phone']}`\n"
        f"📍 **Адрес:** {data['address']}\n"
        f"💐 **Заказ:** {data['items']}\n"
        f"💰 **Сумма:** {data['total']}₽"
    )
    await bot.send_message(MY_ID, admin_msg, reply_markup=get_admin_kb(message.from_user.id), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("accept_") | F.data.startswith("reject_"))
async def process_callback(callback: types.CallbackQuery):
    action, user_id = callback.data.split("_")
    user_id = int(user_id)
    
    if action == "accept":
        await bot.send_message(
            user_id, 
            f"✅ **Ваш заказ подтвержден!**\n\nДля завершения оплаты переведите сумму на карту:\n\n{PAYMENT_DETAILS}\n\n"
            "📸 **ОБЯЗАТЕЛЬНО: Пришлите скриншот чека сюда в чат!**",
            parse_mode="Markdown"
        )
        await callback.message.edit_text(callback.message.text + "\n\n✅ **ОДОБРЕНО. Ждем чек.**")
    else:
        await bot.send_message(user_id, "❌ Извините, на это время все курьеры заняты.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ **ОТКЛОНЕНО**")
    
    await callback.answer()

# --- ЛОГИКА ПРИЕМА ЧЕКА ---
@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    # Если это ты сам себе шлешь для теста — бот просто ответит
    await message.answer("✅ **Чек получен!** Мы проверяем оплату и начинаем сборку букета.")
    
    # Пересылка чека админу (тебе)
    caption = f"🧾 **НОВЫЙ ЧЕК НА ОПЛАТУ**\nОт: @{message.from_user.username}\nID: `{message.from_user.id}`"
    await bot.send_photo(
        chat_id=MY_ID, 
        photo=message.photo[-1].file_id, 
        caption=caption, 
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
