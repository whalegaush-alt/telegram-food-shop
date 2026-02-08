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

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
APP_URL = os.getenv("WEB_APP_URL", "").rstrip('/')

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Открыть магазин 🛍", web_app=WebAppInfo(url=APP_URL)))
    if message.from_user.id == ADMIN_ID:
        builder.row(KeyboardButton(text="Админ-панель ⚙️", web_app=WebAppInfo(url=f"{APP_URL}/admin")))
    await message.answer("Witamy в нашем магазине! Выбирайте товары ниже:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        items = data.get("items", [])
        total = data.get("total", "0 zł")

        res = "🛍 **Новый заказ:**\n" + "—"*15 + "\n"
        for i in items:
            res += f"🔹 {i['name']} x{i['qty']} = {float(i['qty'])*float(i['price'])} zł\n"
        res += "—"*15 + f"\n💰 **Итого: {total}**"
        
        await message.answer(res, parse_mode="Markdown")
        if ADMIN_ID:
            await bot.send_message(ADMIN_ID, f"🔔 **ЗАКАЗ** от @{message.from_user.username or message.from_user.id}\n\n{res}", parse_mode="Markdown")
    except Exception as e:
        logging.error(e)

@app.get("/", response_class=HTMLResponse)
async def shop_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("shop.html", {"request": request, "items": items})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("admin.html", {"request": request, "items": items})

@app.post("/add")
async def add_item(name: str = Form(...), price: float = Form(...), photo: str = Form(...), category: str = Form(...), db: Session = Depends(get_db)):
    db.add(Item(name=name, price=price, photo_url=photo, category=category))
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
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
