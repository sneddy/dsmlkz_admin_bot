import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from dsmlkz_admin_bot.communication.message_handlers import register_message_handlers
from configs.config import BOT_TOKEN

# ENV VARS
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("❌ WEBHOOK_URL not set in environment variables")

# Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
Bot.set_current(bot)
dp = Dispatcher(bot)
register_message_handlers(dp, bot)


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Setting webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)
    yield
    print("🧹 Removing webhook")
    await bot.delete_webhook()


# FastAPI app
app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    update = types.Update(**await req.json())
    await dp.process_update(update)
    return {"status": "ok"}
