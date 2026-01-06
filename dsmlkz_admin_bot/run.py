import logging
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from fastapi import FastAPI, Request

from configs.config import BOT_TOKEN
from dsmlkz_admin_bot.communication.message_handlers import \
    register_message_handlers

# ENV VARS
WEBHOOK_PATH = "/webhook"
# Prefer explicit WEBHOOK_URL, otherwise fall back to Railway-provided domains.
webhook_origin = (
    os.getenv("WEBHOOK_URL")
    or os.getenv("RAILWAY_STATIC_URL")
    or os.getenv("RAILWAY_PUBLIC_DOMAIN")
)
if not webhook_origin:
    raise RuntimeError("❌ WEBHOOK_URL not set and no Railway domain env found")
WEBHOOK_URL = (
    webhook_origin
    if webhook_origin.endswith(WEBHOOK_PATH)
    else f"{webhook_origin.rstrip('/')}{WEBHOOK_PATH}"
)

logger = logging.getLogger(__name__)

# Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
Bot.set_current(bot)
dp = Dispatcher(bot)
register_message_handlers(dp, bot)


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="new_jd", description="Создать вакансию по тексту"),
        # Добавь здесь другие команды, если они есть
    ]
    await bot.set_my_commands(commands)


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting bot with webhook_url=%s port=%s",
        WEBHOOK_URL,
        os.getenv("PORT"),
    )
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("🚀 Webhook set")
    yield
    await bot.delete_webhook()
    logger.info("🧹 Webhook removed, closing session")
    await bot.session.close()

# FastAPI app
app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    try:
        payload = await req.json()
    except Exception:
        logger.exception("Failed to parse webhook payload")
        return {"status": "error", "detail": "invalid json"}

    logger.info(
        "Webhook received: path=%s client=%s size=%s",
        req.url.path,
        req.client.host if req.client else "unknown",
        req.headers.get("content-length"),
    )

    update = types.Update(**payload)
    try:
        await dp.process_update(update)
        logger.info(
            "Processed update: update_id=%s message_id=%s callback_query_id=%s",
            update.update_id,
            getattr(update.message, "message_id", None),
            getattr(update.callback_query, "id", None),
        )
    except Exception:
        logger.exception("Error while processing update: %s", payload)
        raise

    return {"status": "ok"}
