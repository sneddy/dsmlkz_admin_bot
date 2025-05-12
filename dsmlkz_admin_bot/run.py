import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling  # ✅ оставляем, нужен для dev
from dsmlkz_admin_bot.communication.message_handlers import register_message_handlers
from configs.config import BOT_TOKEN

# ENV VARS
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://yourapp.up.railway.app/webhook
ENV = os.getenv("ENV", "dev")  # 'dev' or 'production'

# Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
register_message_handlers(dp, bot)

# 🌐 Webhook (production)
app = FastAPI()


@app.on_event("startup")
async def on_startup():
    if ENV == "production":
        await bot.set_webhook(WEBHOOK_URL)
        print(f"🚀 Webhook set: {WEBHOOK_URL}")


@app.on_event("shutdown")
async def on_shutdown():
    if ENV == "production":
        await bot.delete_webhook()
        print("🧹 Webhook removed")


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    update = types.Update(**await req.json())
    await dp.process_update(update)
    return {"status": "ok"}


# 🤖 Polling (development)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if ENV == "production":
        import uvicorn

        uvicorn.run("run:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    else:
        print("🧪 Running bot in polling mode (dev)")
        start_polling(dp, skip_updates=True)
