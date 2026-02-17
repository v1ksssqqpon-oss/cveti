import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- ПРОВЕРЬ ЭТИ ДАННЫЕ ---
TOKEN = '8517678651:AAGWCBa2BsWTS7M9HzTo7JWet6encABiKWE'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Статистика в памяти (безопасно для Railway)
stats = {"orders": 0, "revenue": 0}

@dp.message(Command("start"))
async def start(message: types.Message):
    # ЭТО ВИДЯТ ВСЕ ПОЛЬЗОВАТЕЛИ
    kb = [[types.KeyboardButton(text="💐 ОТКРЫТЬ МАГАЗИН", web_app=types.WebAppInfo(url=URL))]]
    await message.answer(
        "🌸 **Добро пожаловать в Flower Boutique!**\n\nНажмите на кнопку ниже, чтобы выбрать букет. По всем вопросам — жмите кнопку связи внутри магазина!", 
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
        parse_mode="Markdown"
    )
    
    # А ЭТО ДОПОЛНИТЕЛЬНО ВИДИШЬ ТОЛЬКО ТЫ
    if message.from_user.id == ADMIN_ID:
        admin_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Показать выручку", callback_data="get_stats")]
        ])
        await message.answer("⚙️ **Панель управления:**", reply_markup=admin_kb)

@dp.callback_query(F.data == "get_stats")
async def show_stats(call: types.CallbackQuery):
    await call.message.answer(f"📈 **ОТЧЕТ:**\nВсего заказов: {stats['orders']}\nВыручка: {stats['revenue']}₽")
    await call.answer()

@dp.message(F.web_app_data)
async def handle_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        # Обновляем статы
        stats["orders"] += 1
        stats["revenue"] += int(data['total'])
        
        # Сообщение ТЕБЕ (Админу)
        admin_msg = (
            f"🔥 **НОВЫЙ ЗАКАЗ!**\n\n"
            f"👤 Клиент: {data['name']}\n"
            f"📞 Телефон: `{data['phone']}`\n"
            f"📍 Адрес: {data['address']}\n"
            f"💐 Букеты: {data['items']}\n"
            f"💰 Сумма: **{data['total']}₽**"
        )
        
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        
        # Сообщение КЛИЕНТУ
        await message.answer("✅ **Заказ принят!**\nМы уже начали собирать ваш букет и скоро свяжемся с вами.")
        
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка: {e}")

async def main():
    print("🚀 БОТ ЗАПУЩЕН")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
