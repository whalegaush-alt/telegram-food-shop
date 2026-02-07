import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_URL = os.getenv("WEB_URL")

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
        <p>🍔 Бургер — 25 zł</p>
        <p>🥗 Салат — 18 zł</p>
        <p>🥤 Напиток — 6 zł</p>
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
    await message.answer("Добро пожаловать в магазин 🍔", reply_markup=keyboard)

# ---------- START BOT ----------
async def start_bot():
    executor.start_polling(dp, skip_updates=True)

# ---------- START ALL ----------
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
)
