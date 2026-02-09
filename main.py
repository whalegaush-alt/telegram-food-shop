import os
import asyncio
import logging
import json
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.orm import Session
import uvicorn

from database import SessionLocal, Item

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка настроек из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("WEB_APP_URL", "").rstrip('/')

# Обработка списка админов (принимает строку вида "123,456,789")
ADMINS_RAW = os.getenv("ADMIN_ID", "0")
ADMIN_IDS = [int(id.strip()) for id in ADMINS_RAW.split(",") if id.strip().isdigit()]

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    # Кнопка магазина для всех
    builder.row(KeyboardButton(text="Открыть магазин 🛍", web_app=WebAppInfo(url=APP_URL)))
    
    # Кнопка админки только для списка ADMIN_IDS
    if message.from_user.id in ADMIN_IDS:
        builder.row(KeyboardButton(text="Админ-панель ⚙️", web_app=WebAppInfo(url=f"{APP_URL}/admin")))
    
    await message.answer(
        f"Witamy, {message.from_user.first_name}! 👋\nВыберите товары в нашем меню ниже:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        # Получаем данные из Mini App
        data = json.loads(message.web_app_data.data)
        items = data.get("items", [])
        total_str = data.get("total", "0 zł")

        # Формируем чек для пользователя
        receipt = "🛍 **Ваш заказ принят!**\n"
        receipt += "—" * 15 + "\n"
        for item in items:
            # Считаем сумму строки (qty * price)
            line_sum = float(item['qty']) * float(item['price'])
            receipt += f"🔹 {item['name']} x{item['qty']} = {line_sum:.2f} zł\n"
        
        receipt += "—" * 15 + "\n"
        receipt += f"💰 **Итого к оплате: {total_str}**"
        
        await message.answer(receipt, parse_mode="Markdown")

        # Рассылка уведомления всем администраторам
        user = message.from_user
        username = f"@{user.username}" if user.username else f"ID: {user.id}"
        admin_msg = f"🔔 **НОВЫЙ ЗАКАЗ** от {username}\n\n" + receipt
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Ошибка отправки админу {admin_id}: {e}")
            
    except Exception as e:
        logging.error(f"Ошибка обработки данных WebApp: {e}")
        await message.answer("⚠️ Произошла ошибка при оформлении заказа. Попробуйте снова.")

# --- ЛОГИКА WEB-СЕРВЕРА (FastAPI) ---

@app.get("/", response_class=HTMLResponse)
async def shop_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("shop.html", {"request": request, "items": items})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("admin.html", {"request": request, "items": items})

@app.post("/add")
async def add_item(
    name: str = Form(...), 
    price: float = Form(...), 
    photo: str = Form(...), 
    category: str = Form(...), 
    db: Session = Depends(get_db)
):
    new_item = Item(name=name, price=price, photo_url=photo, category=category)
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/delete/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.on_event("startup")
async def on_startup():
    # Запуск бота в фоновом режиме при старте сервера
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    # Порт для Railway
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
