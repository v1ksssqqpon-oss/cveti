import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- ТВОИ ДАННЫЕ (ПРОВЕРЬ ИХ) ---
TOKEN = '8387192018:AAG_yJ0JEwX0v_lsF8pVkSA74ZpqaaHR5Jo'
ADMIN_ID = 1655167987 
URL = "https://v1ksssqqpon-oss.github.io/cveti/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки админа
def get_admin_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="broadcast")],
        [types.InlineKeyboardButton(text="🎁 Изменить промокод", callback_data="edit_promo")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="💐 ВЫБРАТЬ ЦВЕТЫ", web_app=types.WebAppInfo(url=URL))]]
    await message.answer("🌸 **Flower Boutique** готов к работе!\nВыбирай букеты в меню ниже:", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
                         parse_mode="Markdown")
    
    # Если это ты, показываем админку
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 **Панель управления:**", reply_markup=get_admin_kb())

@dp.message(F.web_app_data)
async def handle_order(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        # Текст для тебя (админа)
        admin_text = (
            f"🚀 **НОВЫЙ ЗАКАЗ!**\n\n"
            f"👤 Клиент: {data['name']}\n"
            f"📞 Телефон: `{data['phone']}`\n"
            f"📍 Адрес: {data['address']}\n"
            f"💐 Состав: {data['items']}\n"
            f"💰 Сумма: **{data['total']}₽**"
        )
        
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        await message.answer("✨ **Заказ принят!**\nНаш флорист уже подбирает лучшие цветы для вас.")
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка в данных: {e}")

async def main():
    print("🚀 БОТ ЗАПУЩЕН И ГОТОВ К ПРОДАЖАМ")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
