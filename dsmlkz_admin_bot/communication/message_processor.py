import logging
import uuid

import aiohttp
from aiogram import Bot, types
from supabase import create_client

from configs.config import SUPABASE_BUCKET, SUPABASE_KEY, SUPABASE_URL
from dsmlkz_admin_bot.parsing import BaseParsing, JobsParsing, ParsedMessage

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

log = logging.getLogger(__name__)


class MessageProcessor:
    """
    MessageProcessor handles the complete pipeline for processing Telegram messages:
    - Parsing forwarded messages based on type (jobs/news).
    - Downloading attached images from Telegram.
    - Uploading images to Supabase storage.
    - Saving parsed message content and image URLs to the Supabase database.

    Usage example:
        processor = MessageProcessor(bot, message)
        await processor.process_message('job')
    """

    def __init__(self, bot: Bot, message: types.Message, bucket: str = SUPABASE_BUCKET):
        """
        Initializes the MessageProcessor instance.

        :param bot: Aiogram Bot instance.
        :param message: Aiogram message object received from Telegram.
        """
        self.bot = bot
        self.message = message
        self.bucket = bucket
        log.info(
            "Initialized MessageProcessor: message_id=%s user=%s chat=%s fwd_from=%s has_photo=%s text_len=%s caption_len=%s",
            message.message_id,
            getattr(message.from_user, "id", None),
            getattr(message.chat, "id", None),
            getattr(getattr(message, "forward_from_chat", None), "id", None),
            bool(message.photo),
            len(message.text or "") if message.text else 0,
            len(message.caption or "") if getattr(message, "caption", None) else 0,
        )

    async def parse_job(self):
        """Parses job-type messages into structured format."""
        parser = JobsParsing()
        parsed = parser.parse(self.message)
        log.info(
            "Parsed job message: message_id=%s meta_keys=%s",
            self.message.message_id,
            list(parsed.meta_information.keys()),
        )
        return parsed

    async def parse_news(self):
        """Parses news-type messages into structured format."""
        parser = BaseParsing()
        parsed = parser.parse(self.message)
        log.info(
            "Parsed news message: message_id=%s meta_keys=%s",
            self.message.message_id,
            list(parsed.meta_information.keys()),
        )
        return parsed

    async def download_image(self, file_id: str) -> bytes:
        """
        Downloads an image from Telegram servers by file_id.

        :param file_id: Telegram file_id.
        :return: Image bytes.
        """
        file_info = await self.bot.get_file(file_id)
        file_url = (
            f"https://api.telegram.org/file/bot{self.bot._token}/{file_info.file_path}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                response.raise_for_status()
                data = await response.read()
                log.info(
                    "Downloaded image from Telegram: file_id=%s size=%s bytes path=%s",
                    file_id,
                    len(data),
                    file_info.file_path,
                )
                return data

    async def store_image(self):
        """
        Downloads the attached image from the Telegram message and uploads it to Supabase storage.

        :return: URL of the stored image or None if no image exists.
        """
        if self.message.photo:
            photo = self.message.photo[-1]
            image_bytes = await self.download_image(photo.file_id)
            image_url = await self.upload_image_to_supabase(image_bytes)
            return image_url
        return None

    async def upload_image_to_supabase(self, image_bytes: bytes) -> str:
        """
        Uploads image bytes to Supabase storage.

        :param image_bytes: Raw image data.
        :param bucket: Supabase bucket name.
        :return: Public URL of the stored image.
        """
        image_name = f"{uuid.uuid4()}.jpg"
        result = supabase.storage.from_(self.bucket).upload(
            image_name, image_bytes, {"content-type": "image/jpeg"}
        )
        if result.status_code != 200:
            raise Exception(f"Upload failed: {result.content}")

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{self.bucket}/{image_name}"
        log.info(
            "Uploaded image to Supabase: name=%s status=%s public_url=%s",
            image_name,
            result.status_code,
            public_url,
        )

        return public_url

    async def save_message(self, data: dict, table: str = "channels_content"):
        """
        Saves parsed message data to the Supabase database.

        :param data: Parsed message dictionary.
        :param table: Supabase table name to store data.
        :return: Supabase response.
        """
        result = supabase.table(table).insert(data).execute()
        if hasattr(result, "error") and result.error:
            raise Exception(f"DB insert failed: {result.error}")
        log.info(
            "Saved data to Supabase: table=%s count=%s", table, len(result.data or [])
        )
        return result

    async def save_parsed_message(self, parsed_message: ParsedMessage):
        """
        Converts a parsed message into a dictionary and saves it to the database.

        :param parsed_message: ParsedMessage instance.
        """
        post_id = str(uuid.uuid4())
        data = parsed_message.to_channels_content_dict(post_id)
        await self.save_message(data)
        if parsed_message.source == "jobs":
            job_details = parsed_message.other.copy()
            job_details["post_id"] = post_id
            await self.save_message(job_details, table="job_details")

    async def process_message(self, message_type: str = "news"):
        """
        Complete pipeline to process a Telegram message:
        1. Parses the message content (job or news).
        2. Downloads and uploads images, if present.
        3. Saves parsed content and image URLs into the database.

        :param message_type: Type of message to parse ("job" or "news").
        :return: ParsedMessage instance after processing.
        """
        parsed_message = (
            await self.parse_job() if message_type == "job" else await self.parse_news()
        )

        image_url = await self.store_image()
        if image_url:
            parsed_message.image_url = image_url
            log.info(
                "Attached image URL to parsed message: message_id=%s url=%s",
                self.message.message_id,
                image_url,
            )

        await self.save_parsed_message(parsed_message)
        log.info(
            "Completed processing message: message_id=%s type=%s channel=%s post_link=%s",
            self.message.message_id,
            message_type,
            parsed_message.meta_information.get("channel_name"),
            parsed_message.meta_information.get("post_link"),
        )

        return parsed_message
