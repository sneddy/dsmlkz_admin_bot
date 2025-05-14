from aiogram import Bot, Dispatcher, types
from dsmlkz_admin_bot.communication.message_processor import MessageProcessor
from dsmlkz_admin_bot.keyboards import get_action_keyboard, get_confirmation_keyboard
from dsmlkz_admin_bot.communication.new_jd_handler import register_new_jd

# Temporary in-memory storage
user_message_storage = {}


async def clean_up_messages(bot: Bot, user_id: int, message_ids: list):
    """Safely delete messages."""
    for msg_id in message_ids:
        if msg_id:
            try:
                await bot.delete_message(user_id, msg_id)
            except Exception:
                pass
    user_message_storage.pop(user_id, None)


def register_message_handlers(dp: Dispatcher, bot: Bot):
    # Temporary media group tracking
    register_new_jd(dp)
    media_group_cache = {}

    @dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO])
    async def handle_forwarded(message: types.Message):
        if not message.forward_from_chat:
            await message.reply("⚠️ Please forward a message from a channel.")
            return

        # Skip if we've already handled this media group
        if message.media_group_id:
            cached_group = media_group_cache.get(message.from_user.id)
            if cached_group == message.media_group_id:
                return  # Already handled
            media_group_cache[message.from_user.id] = message.media_group_id

        processor = MessageProcessor(bot, message)
        user_message_storage[message.from_user.id] = {
            "processor": processor,
            "message": message,
        }

        control_message = await message.reply(
            "What do you want to do with this message?",
            reply_markup=get_action_keyboard(),
        )

        user_message_storage[message.from_user.id][
            "control_message_id"
        ] = control_message.message_id

    @dp.callback_query_handler(
        lambda c: c.data
        in [
            "parse_job",
            "parse_news",
            "confirm_save",
            "cancel_action",
            "cancel_save",
            "decline_save",
        ]
    )
    async def handle_callback(callback_query: types.CallbackQuery):
        user_id = callback_query.from_user.id
        storage = user_message_storage.get(user_id)

        if not storage:
            await callback_query.answer(
                "Please forward a message first.", show_alert=True
            )
            return

        processor: MessageProcessor = storage["processor"]
        message = storage["message"]
        control_message_id = storage.get("control_message_id")

        # 🧹 Cleanup on cancel/decline
        if callback_query.data in ["cancel_action", "cancel_save", "decline_save"]:
            await clean_up_messages(
                bot,
                user_id,
                [
                    control_message_id,
                    storage.get("preview_message_id"),
                    storage.get("confirmation_message_id"),
                    message.message_id,
                ],
            )
            await callback_query.answer("❌ Action cancelled.", show_alert=False)
            return

        # ✅ Parse job/news
        if callback_query.data in ["parse_job", "parse_news"]:
            message_type = "job" if callback_query.data == "parse_job" else "news"
            parsed_message = (
                await processor.parse_job()
                if message_type == "job"
                else await processor.parse_news()
            )

            storage["parsed_message"] = parsed_message

            preview_message = await bot.send_message(
                user_id, parsed_message.full_text_html, parse_mode="HTML"
            )
            confirmation_message = await bot.send_message(
                user_id,
                "Do you want to save this record to the database?",
                reply_markup=get_confirmation_keyboard(),
            )

            storage["preview_message_id"] = preview_message.message_id
            storage["confirmation_message_id"] = confirmation_message.message_id

        # 💾 Confirm Save
        if callback_query.data == "confirm_save":
            parsed_message = storage.get("parsed_message")
            if parsed_message:
                image_url = await processor.store_image()
                if image_url:
                    parsed_message.image_url = image_url

                await processor.save_parsed_message(parsed_message)
                await callback_query.answer(
                    "✅ Successfully saved to DB!", show_alert=True
                )

            await clean_up_messages(
                bot,
                user_id,
                [
                    control_message_id,
                    storage.get("preview_message_id"),
                    storage.get("confirmation_message_id"),
                    message.message_id,
                ],
            )
