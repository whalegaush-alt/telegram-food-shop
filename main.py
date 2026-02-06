import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_URL = os.getenv("WEB_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ---------- FASTAPI ----------
app = FastAPI()

@app.get("/shop", response_class=HTMLResponse)
async def shop():
    return """
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Магазин</title>
        </head>
        <body>
            <h2>🛒 Онлайн-магазин</h2>
            <p>🍔 Бургеры — 25 zł</p>
            <p>🥗 Салаты — 18 zł</p>
            <p>🥤 Напитки — 6 zł</p>
            <button onclick="alert('Скоро будет корзина 😄')">
                Добавить в корзину
            </button>
        </body>
    </html>
    """

# ---------- BOT ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton(
            text="🛒 Открыть магазин",
            web_app=types.WebAppInfo(url=f"{WEB_URL}/shop")
        )
    )

    await message.answer(
        "Добро пожаловать в онлайн-магазин 🍔🥦",
        reply_markup=keyboard
    )

# ---------- RUN BOTH ----------
async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    )
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
