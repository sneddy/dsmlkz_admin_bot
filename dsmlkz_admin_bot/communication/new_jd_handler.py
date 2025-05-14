from aiogram import types, Dispatcher
from dsmlkz_admin_bot.services.hr_assistant_service import ChatGptHrAssistant
from dsmlkz_admin_bot.services.jd_drawing_service import JobDrawer
import os
import tempfile

assistant = ChatGptHrAssistant(api_key=os.getenv("OPENAI_API_KEY"))
drawer = JobDrawer(
    img_path="assets/job_template.png",  # путь к шаблону
    font_path="assets/fonts/Bold.ttf",  # путь к жирному шрифту
    description_font_path="assets/fonts/Regular.ttf",  # путь к описательному шрифту
)

user_states = {}


async def start_new_jd(message: types.Message):
    user_states[message.from_user.id] = "awaiting_jd"
    await message.reply("Пожалуйста, пришлите описание вакансии свободным текстом.")


async def handle_jd(message: types.Message):
    if user_states.get(message.from_user.id) != "awaiting_jd":
        return

    jd_text = message.text
    await message.reply("Генерирую вакансию...")

    try:
        meta_info = assistant.text2dict(jd_text)
        meta_info = assistant.replace_markdown_symbols(meta_info)

        drawer.reset()
        img = drawer.draw(meta_info)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_img_path = tmp.name
            img.save(temp_img_path)

        with open(temp_img_path, "rb") as photo_file:
            await message.answer_photo(photo_file)

        os.remove(temp_img_path)

        markdown_text = assistant.dict2markdown(meta_info)
        await message.reply(markdown_text, parse_mode="MarkdownV2")

    except Exception as e:
        await message.reply(f"Произошла ошибка при генерации: {e}")
    finally:
        user_states.pop(message.from_user.id, None)


def register_new_jd(dp: Dispatcher):
    dp.register_message_handler(start_new_jd, commands=["new_jd"])
    dp.register_message_handler(handle_jd, content_types=types.ContentTypes.TEXT)
