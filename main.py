import os
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

# ------------------ ENV ------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_URL = os.getenv("WEB_URL")        # без слеша на конце
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ------------------ BOT ------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ------------------ DATA ------------------
products = []
product_id = 1

# ------------------ FASTAPI LIFESPAN ------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 Bot polling started")
    task = asyncio.create_task(dp.start_polling())
    yield
    logging.info("🛑 Bot stopping")
    task.cancel()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ------------------ SHOP ------------------
@app.get("/shop", response_class=HTMLResponse)
async def shop():
    html = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:sans-serif; padding:10px; background:#f5f5f5">
      <h2>🛒 Магазин</h2>
    """

    if not products:
        html += "<p>Пока нет товаров</p>"

    for p in products:
        html += f"""
        <div style="background:#fff; padding:10px; margin-bottom:10px;
                    border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,.1)">
            <img src="{p['photo']}" width="120"><br><br>
            <b>{p['name']}</b><br>
            💰 {p['price']} zł
        </div>
        """

    html += "</body></html>"
    return html

# ------------------ ADMIN PANEL ------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return """
    <html>
    <body style="font-family:sans-serif; padding:20px">
        <h2>⚙️ Админка</h2>
        <form action="/admin/add" method="post">
            <input name="name" placeholder="Название" required><br><br>
            <input name="price" type="number" placeholder="Цена" required><br><br>
            <input name="photo" placeholder="URL фото" required><br><br>
            <button type="submit">➕ Добавить товар</button>
        </form>
    </body>
    </html>
    """

@app.post("/admin/add", response_class=HTMLResponse)
async def admin_add(
    name: str = Form(...),
    price: int = Form(...),
    photo: str = Form(...)
):
    global product_id
    products.append({
        "id": product_id,
        "name": name,
        "price": price,
        "photo": photo
    })
    product_id += 1

    return """
    <h3>✅ Товар добавлен</h3>
    <a href="/admin">← Назад</a>
    """

# ------------------ BOT COMMANDS ------------------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        types.KeyboardButton(
            text="🛒 Открыть магазин",
            web_app=types.WebAppInfo(url=f"{WEB_URL}/shop")
        )
    )
    await message.answer("Добро пожаловать 👋", reply_markup=kb)

@dp.message_handler(commands=["admin"])
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        types.KeyboardButton(
            text="⚙️ Админка",
            web_app=types.WebAppInfo(url=f"{WEB_URL}/admin")
        )
    )
    await message.answer("Админ-панель 👑", reply_markup=kb)

# ------------------ RUN ------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
