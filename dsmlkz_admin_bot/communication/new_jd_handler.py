import os
import tempfile

from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from dsmlkz_admin_bot.services.hr_assistant_service import ChatGptHrAssistant
from dsmlkz_admin_bot.services.jd_drawing_service import JobDrawer

user_states = {}


def get_job_type_keyboard():
    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💻 IT Jobs", callback_data="job_type:it"),
                InlineKeyboardButton(text="🧠 ML Jobs", callback_data="job_type:ml"),
            ]
        ],
    )


async def start_new_jd(message: types.Message):
    await message.reply("Выберите тип вакансии:", reply_markup=get_job_type_keyboard())


async def job_type_callback(call: types.CallbackQuery):
    job_type = call.data.split(":")[1]
    user_states[call.from_user.id] = {"state": "awaiting_jd", "job_type": job_type}
    await call.message.edit_reply_markup()
    await call.message.answer("Теперь пришлите описание вакансии.")


async def handle_jd(message: types.Message):
    user_state = user_states.get(message.from_user.id, {})
    if user_state.get("state") != "awaiting_jd":
        return

    if not message.text:
        await message.reply("Пожалуйста, отправьте текст вакансии.")
        return

    job_type = user_state.get("job_type", "it")

    if job_type == "ml":
        drawer = JobDrawer(
            img_path="assets/images/ml_job_template.jpeg",
            font_path="assets/fonts/PressStart2P-Regular.ttf",
            description_font_path="assets/fonts/NotoSans-Regular.ttf",
        )
    else:
        drawer = JobDrawer(
            img_path="assets/images/it_job_template.jpeg",
            font_path="assets/fonts/PressStart2P-Regular.ttf",
            description_font_path="assets/fonts/NotoSans-Regular.ttf",
        )

    assistant = ChatGptHrAssistant(api_key=os.getenv("OPENAI_API_KEY"))

    await message.reply("Генерирую вакансию...")

    try:
        meta_info = assistant.text2dict(message.text)

        drawer.reset()
        img = drawer.draw(meta_info)
        meta_info = assistant.replace_markdown_symbols(meta_info)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_img_path = tmp.name
            img.save(temp_img_path)

        try:
            with open(temp_img_path, "rb") as photo_file:
                await message.answer_photo(photo_file)
        finally:
            os.remove(temp_img_path)

        markdown_text = assistant.dict2markdown(meta_info)
        await message.reply(markdown_text, parse_mode="MarkdownV2")

    except Exception as e:
        await message.reply(f"Произошла ошибка при генерации: {e}")
    finally:
        user_states.pop(message.from_user.id, None)


def register_new_jd(dp: Dispatcher):
    dp.register_message_handler(start_new_jd, commands=["new_jd"])
    dp.register_callback_query_handler(
        job_type_callback, lambda c: c.data.startswith("job_type:")
    )
    dp.register_message_handler(handle_jd, content_types=types.ContentTypes.TEXT)
