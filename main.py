import os
import asyncio
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from sqlalchemy.orm import Session
import uvicorn

from database import SessionLocal, Item

# Настройки из переменных Railway
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
APP_URL = os.getenv("WEB_APP_URL") # Например: https://your-project.up.railway.app

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Получение сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЛОГИКА БОТА ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    kb = [
        [KeyboardButton(text="Открыть магазин 🛍", web_app=WebAppInfo(url=APP_URL))]
    ]
    if message.from_user.id == ADMIN_ID:
        kb.append([KeyboardButton(text="Админ-панель ⚙️", web_app=WebAppInfo(url=f"{APP_URL}/admin"))])
    
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Привет! Я бот-магазин.", reply_markup=markup)

# --- ЛОГИКА WEB-APP ---
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

# Запуск бота в фоне
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
