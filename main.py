import os
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import json

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_URL = os.getenv("WEB_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Telegram ID админа

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ---------- LIFESPAN ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Starting bot polling...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    try:
        yield
    finally:
        logging.info("Stopping bot...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ---------- SHOP PAGE ----------
@app.get("/shop", response_class=HTMLResponse)
async def shop():
    return f"""
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: sans-serif; text-align: center; padding: 20px; background: #f4f4f4; }}
            .item {{ background: white; padding: 10px; margin: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            button {{ margin: 0 5px; }}
        </style>
      </head>
      <body>
        <h2>🛒 Онлайн-магазин</h2>

        <div class="item">
            🍔 Бургер — 25 zł
            <button onclick="addToCart('Бургер', 25)">+</button>
            <span id="Бургер-count">0</span>
            <button onclick="removeFromCart('Бургер')">−</button>
        </div>

        <div class="item">
            🥗 Салат — 18 zł
            <button onclick="addToCart('Салат', 18)">+</button>
            <span id="Салат-count">0</span>
            <button onclick="removeFromCart('Салат')">−</button>
        </div>

        <div class="item">
            🥤 Напиток — 6 zł
            <button onclick="addToCart('Напиток', 6)">+</button>
            <span id="Напиток-count">0</span>
            <button onclick="removeFromCart('Напиток')">−</button>
        </div>

        <div id="total">Итого: 0 zł</div>
        <button onclick="checkout()">Оформить заказ</button>

        <script>
            const cart = {{}};

            function addToCart(name, price){{
                if(!cart[name]) cart[name] = 0;
                cart[name]++;
                document.getElementById(`${{name}}-count`).innerText = cart[name];
                updateTotal();
            }}

            function removeFromCart(name){{
                if(cart[name]){{ cart[name]--; if(cart[name]<0) cart[name]=0; }}
                document.getElementById(`${{name}}-count`).innerText = cart[name];
                updateTotal();
            }}

            function updateTotal(){{
                let total = 0;
                for(let item in cart){{
                    let price = 0;
                    if(item=="Бургер") price=25;
                    if(item=="Салат") price=18;
                    if(item=="Напиток") price=6;
                    total += cart[item]*price;
                }}
                document.getElementById('total').innerText = "Итого: " + total + " zł";
            }}

            function checkout(){{
                Telegram.WebApp.sendData(JSON.stringify(cart));
            }}
        </script>
      </body>
    </html>
    """

# ---------- BOT HANDLERS ----------
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

@dp.message_handler(content_types=["web_app_data"])
async def handle_order(message: types.Message):
    order = json.loads(message.web_app_data.data)
    text = "Новый заказ:\n" + "\n".join([f"{k}: {v}" for k,v in order.items()])
    await message.answer("Спасибо! Ваш заказ принят ✅")
    # Отправка админу
    await bot.send_message(ADMIN_ID, f"Заказ от {message.from_user.full_name} (@{message.from_user.username}):\n{text}")

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
