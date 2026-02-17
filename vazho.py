import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- ТВОИ ДАННЫЕ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
MY_ID = 1655167987 

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    # Кнопка открытия твоего Mini App (ссылка на GitHub Pages)
    kb = [[types.KeyboardButton(text="🌸 ОТКРЫТЬ МАГАЗИН", 
                                web_app=types.WebAppInfo(url="https://v1ksssqqpon-oss.github.io/cveti/"))]]
    await message.answer("Добро пожаловать в Flower Boutique! 💐",
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    # Сообщение тебе (админу)
    admin_msg = (
        f"🔥 **НОВЫЙ ЗАКАЗ**\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Тел: `{data['phone']}`\n"
        f"📍 Адрес: {data['address']}\n"
        f"💐 Заказ: {data['items']}\n"
        f"💰 Итого: {data['total']}₽"
    )
    await bot.send_message(MY_ID, admin_msg, parse_mode="Markdown")
    await message.answer("✨ Заказ принят! Скоро свяжемся с вами.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
