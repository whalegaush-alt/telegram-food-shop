import os
import asyncio
import logging
import json
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.orm import Session
import uvicorn

from database import SessionLocal, Item

# 1. Настройка логов
logging.basicConfig(level=logging.INFO)

# 2. Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
APP_URL = os.getenv("WEB_APP_URL", "").rstrip('/')

# 3. Инициализация бота и сервера
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 4. Работа с БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЛОГИКА БОТА ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    # Кнопка для открытия магазина
    builder.row(KeyboardButton(text="Открыть магазин 🛍", web_app=WebAppInfo(url=APP_URL)))
    
    # Кнопка админки только для владельца
    if message.from_user.id == ADMIN_ID:
        builder.row(KeyboardButton(text="Админ-панель ⚙️", web_app=WebAppInfo(url=f"{APP_URL}/admin")))
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\nДобро пожаловать в наш магазин. Выбирай товары прямо в Telegram!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# ОБРАБОТЧИК ЗАКАЗА (прилетает из Web App)
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        # Распаковываем JSON, который прислал JS из shop.html
        data = json.loads(message.web_app_data.data)
        items = data.get("items", [])
        total = data.get("total", 0)

        # Формируем список товаров для сообщения
        order_text = "\n".join([f"• {item['name']} — {item['price']}₽" for item in items])
        
        # Ответ пользователю
        await message.answer(
            f"✅ **Заказ принят!**\n\n**Ваш список:**\n{order_text}\n\n**Итого к оплате:** {total}₽\n\nМенеджер свяжется с вами в ближайшее время!"
        )

        # Уведомление админу
        if ADMIN_ID:
            user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            await bot.send_message(
                ADMIN_ID,
                f"🔔 **НОВЫЙ ЗАКАЗ!**\n\n**Клиент:** {user_info}\n\n**Товары:**\n{order_text}\n\n**Сумма:** {total}₽"
            )
    except Exception as e:
        logging.error(f"Ошибка при обработке заказа: {e}")
        await message.answer("Произошла ошибка при оформлении заказа. Попробуйте еще раз.")

# --- ВЕБ-ИНТЕРФЕЙС (FastAPI) ---

@app.get("/", response_class=HTMLResponse)
async def shop_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("shop.html", {"request": request, "items": items})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("admin.html", {"request": request, "items": items})

@app.post("/add")
async def add_item(name: str = Form(...), price: float = Form(...), photo: str = Form(...), db: Session = Depends(get_db)):
    new_item = Item(name=name, price=price, photo_url=photo)
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# Удаление товара (опционально)
@app.post("/delete/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# Запуск бота при старте сервера
@app.on_event("startup")
async def on_startup():
    logging.info("Бот начинает опрос серверов Telegram...")
    asyncio.create_task(dp.start_polling(bot))

# Точка входа для Railway
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
