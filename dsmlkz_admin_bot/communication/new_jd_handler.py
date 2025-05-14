from aiogram import types, Dispatcher
from dsmlkz_admin_bot.services.hr_assistant_service import ChatGptHrAssistant
import os

assistant = ChatGptHrAssistant(api_key=os.getenv("OPENAI_API_KEY"))
user_states = {}


async def start_new_jd(message: types.Message):
    user_states[message.from_user.id] = "awaiting_jd"
    await message.reply("Пожалуйста, пришлите описание вакансии свободным текстом.")


async def handle_jd(message: types.Message):
    if user_states.get(message.from_user.id) != "awaiting_jd":
        return

    await message.reply("Генерирую вакансию...")
    jd_text = message.text

    try:
        markdown_output = assistant(jd_text)
        await message.reply(markdown_output, parse_mode="MarkdownV2")
    except Exception as e:
        await message.reply(f"Произошла ошибка при генерации: {e}")
    finally:
        user_states.pop(message.from_user.id, None)


def register_new_jd(dp: Dispatcher):
    dp.register_message_handler(start_new_jd, commands=["new_vacancy"])
    dp.register_message_handler(handle_jd, content_types=types.ContentTypes.TEXT)
