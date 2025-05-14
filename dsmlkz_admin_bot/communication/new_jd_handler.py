# handlers/new_vacancy_handler.py
from aiogram import types, Router, F
from dsmlkz_admin_bot.services.hr_assistant_service import ChatGptHrAssistant
import os

router = Router()
assistant = ChatGptHrAssistant(api_key=os.getenv("OPENAI_API_KEY"))

user_states = {}


@router.message(F.text == "/new_vacancy")
async def start_new_vacancy(message: types.Message):
    user_states[message.from_user.id] = "awaiting_jd"
    await message.reply("Пожалуйста, пришлите описание вакансии свободным текстом.")


@router.message()
async def handle_job_description(message: types.Message):
    if user_states.get(message.from_user.id) != "awaiting_jd":
        return

    jd_text = message.text
    await message.reply("Генерирую вакансию...")

    try:
        markdown_output = assistant(jd_text)
        await message.reply(markdown_output, parse_mode="MarkdownV2")
    except Exception as e:
        await message.reply(f"Произошла ошибка при генерации: {e}")
    finally:
        user_states.pop(message.from_user.id, None)
