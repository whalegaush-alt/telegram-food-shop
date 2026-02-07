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
WEB_URL = os.getenv("WEB_URL")      # без слеша в конце
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

# ------------------ SHOP (ШАГ 1: КОРЗИНА) ------------------
@app.get("/shop", response_class=HTMLResponse)
async def shop():
    html = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <script src="https://telegram.org/js/telegram-web-app.js"></script>
    </head>
    <body style="font-family:sans-serif; padding:10px; background:#f5f5f5">
      <h2>🛒 Магазин</h2>

      <script>
        let cart = {};

        function add(id, name, price) {
          if (!cart[id]) cart[id] = {name:name, price:price, qty:0};
          cart[id].qty++;
          render();
        }

        function removeItem(id) {
          if (cart[id] && cart[id].qty > 0) {
            cart[id].qty--;
            render();
          }
        }

        function render() {
          let total = 0;
          let text = "";
          for (let id in cart) {
            if (cart[id].qty > 0) {
              total += cart[id].qty * cart[id].price;
              text += cart[id].name + " x" + cart[id].qty + "\\n";
            }
          }
          document.getElementById("total").innerText = "Итого: " + total + " zł";
          window.orderText = text + "\\n💰 Итого: " + total + " zł";
        }

        function checkout() {
          if (!window.orderText || window.orderText.trim() === "") {
            alert("Корзина пуста");
            return;
          }
          Telegram.WebApp.sendData(window.orderText);
        }
      </script>
    """

    if not products:
        html += "<p>Пока нет товаров</p>"

    for p in products:
        html += f"""
        <div style="background:#fff; padding:10px; margin-bottom:10px;
                    border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,.1)">
            <img src="{p['photo']}" width="120"><br>
            <b>{p['name']}</b><br>
            💰 {p['price']} zł<br><br>
            <button onclick="add({p['id']}, '{p['name']}', {p['price']})">➕</button>
            <button onclick="removeItem({p['id']})">➖</button>
        </div>
        """

    html += """
      <h3 id="total">Итого: 0 zł</h3>
      <button onclick="checkout()" style="padding:10px; font-size:16px">
        ✅ Оформить заказ
      </button>
    </body>
    </html>
    """
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

# ------------------ ORDER HANDLER ------------------
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def webapp_order(message: types.Message):
    order_text = message.web_app_data.data
    await bot.send_message(
        ADMIN_ID,
        f"📦 Новый заказ\n\n{order_text}"
    )
    await message.answer("✅ Заказ отправлен! Спасибо 🙌")

# ------------------ RUN ------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
