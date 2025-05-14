import asyncio

from aiogram import Bot

from configs.config import BOT_TOKEN
from configs.prev_messages import (aimoldin_jobs_messages, it_jobs_messages,
                                   news_messages)
from dsmlkz_admin_bot.communication.message_processor import MessageProcessor

messages_to_process = {
    # "news": [(-1001055767503, post_id) for post_id in news_messages],
    "jobs": aimoldin_jobs_messages,
}


async def process_batch(
    bot: Bot, user_id: int, messages_by_type: dict[str, list[tuple[int, int]]]
):
    for msg_type, msg_list in messages_by_type.items():
        for channel_id, message_id in msg_list:
            try:
                forwarded = await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=channel_id,
                    message_id=message_id,
                )

                processor = MessageProcessor(bot, forwarded)
                parsed = (
                    await processor.parse_news()
                    if msg_type == "news"
                    else await processor.parse_job()
                )

                image_url = await processor.store_image()
                if image_url:
                    parsed.image_url = image_url
                await processor.save_parsed_message(parsed)

                await bot.delete_message(user_id, forwarded.message_id)

                print(f"✅ Processed: {parsed.meta_information.get('post_link')}")

            except Exception as e:
                print(f"❌ Failed to process ({channel_id}, {message_id}): {e}")


async def main():
    bot = Bot(token=BOT_TOKEN)
    try:
        await process_batch(
            bot, user_id=212657982, messages_by_type=messages_to_process
        )
    finally:
        session = await bot.get_session()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
