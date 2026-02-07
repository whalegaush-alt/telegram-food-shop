import os
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
# Убираем executor, он здесь не нужен

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_URL = os.getenv("WEB_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ---------- LIFESPAN (Замена устаревшему on_event) ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код здесь выполняется при СТАРТЕ приложения
    logging.info("Starting bot polling...")
    polling_task = asyncio.create_task(dp.start_polling())
    
    yield  # Здесь приложение работает
    
    # Код здесь выполняется при ОСТАНОВКЕ приложения
    logging.info("Stopping bot...")
    polling_task.cancel()
    await bot.session.close()

# ---------- FASTAPI ----------
app = FastAPI(lifespan=lifespan)

@app.get("/shop", response_class=HTMLResponse)
async def shop():
    return """
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: sans-serif; text-align: center; padding: 20px; background: #f4f4f4; }
            .item { background: white; padding: 10px; margin: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        </style>
      </head>
      <body>
        <h2>🛒 Онлайн-магазин</h2>
        <div class="item">🍔 Бургер — 25 zł</div>
        <div class="item">🥗 Салат — 18 zł</div>
        <div class="item">🥤 Напиток — 6 zł</div>
      </body>
    </html>
    """

# ---------- BOT ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Убедитесь, что WEB_URL в Railway указан БЕЗ слеша в конце
    url = f"{WEB_URL}/shop"
    keyboard.add(
        types.KeyboardButton(
            text="🛒 Открыть магазин",
            web_app=types.WebAppInfo(url=url)
        )
    )
    await message.answer("Добро пожаловать в магазин 🍔", reply_markup=keyboard)

# ---------- RUN ----------
if __name__ == "__main__":
    # Порт Railway подтягивает автоматически через переменную PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
