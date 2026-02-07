import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Загружаем данные из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) # Твой ID в телеграм
WEB_APP_URL = os.getenv("WEB_APP_URL") # Ссылка на админку (Railway URL)

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_main_keyboard(user_id: int):
    builder = ReplyKeyboardBuilder()
    
    # Кнопка магазина для всех
    builder.row(KeyboardButton(
        text="Открыть магазин 🛍", 
        web_app=WebAppInfo(url=WEB_APP_URL)
    ))
    
    # Кнопка админки только для админа
    if user_id == ADMIN_ID:
        builder.row(KeyboardButton(
            text="Админ-панель ⚙️", 
            web_app=WebAppInfo(url=f"{WEB_APP_URL}/admin")
        ))
        
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Добро пожаловать в магазин.",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
