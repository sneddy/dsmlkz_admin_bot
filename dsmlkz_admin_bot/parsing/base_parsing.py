from aiogram.types import Message
from abc import ABC
from dsmlkz_admin_bot.utils.entities_parser import EntitiesParser
from dsmlkz_admin_bot.parsing.parsed_message import ParsedMessage


class BaseParsing(ABC):
    def extract_meta_info(self, message: Message) -> dict:
        channel_id = ""
        channel_name = ""
        channel_username = None
        forward_msg_id = message.forward_from_message_id or ""

        if message.forward_from_chat:
            channel = message.forward_from_chat
            channel_id = channel.id or ""
            channel_name = channel.title or channel.username or ""
            channel_username = channel.username

        # Created at — from the original post time
        created_at = (
            message.forward_date.strftime("%Y-%m-%d %H:%M:%S")
            if message.forward_date
            else ""
        )

        # Is the channel public?
        is_public = bool(channel_username)

        # Construct post link
        if is_public:
            post_link = f"https://t.me/{channel_username}/{forward_msg_id}"
        else:
            internal_id = str(channel_id).replace("-100", "")
            post_link = f"https://t.me/c/{internal_id}/{forward_msg_id}"

        # Sender info (if forwarded from user)
        sender_id = None
        sender_name = None
        if message.forward_sender_name:
            sender_name = message.forward_sender_name
        elif message.forward_from:
            sender_id = message.forward_from.id
            sender_name = (
                message.forward_from.username
                or f"{message.forward_from.first_name} {message.forward_from.last_name or ''}".strip()
            )

        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "message_id": forward_msg_id,
            "created_at": created_at,
            "post_link": post_link,
            "is_public": is_public,
            "sender_id": sender_id,
            "sender_name": sender_name,
        }

    def extract_image_url(self, message: Message) -> str:
        if message.photo:
            largest_photo = message.photo[-1]
            return largest_photo.file_id
        return ""

    def extract_raw_text(self, message: Message) -> str:
        return message.caption or message.text or ""

    def extract_entities(self, message: Message) -> list:
        return message.entities or message.caption_entities or []

    def extract_html(self, message: Message) -> tuple[str, str]:
        raw_text = self.extract_raw_text(message)
        entities = self.extract_entities(message)
        parser = EntitiesParser(raw_text, entities)
        return parser.html, parser.tg_preview

    def parse(self, message: Message) -> ParsedMessage:
        meta = self.extract_meta_info(message)
        image_url = self.extract_image_url(message)
        raw_text = self.extract_raw_text(message)
        html_text, tg_preview = self.extract_html(message)

        parsed_message = ParsedMessage(
            meta_information=meta,
            image_url=image_url,
            raw_text=raw_text,
            html_text=html_text,
            tg_preview=tg_preview,
            source="base",
        )
        return parsed_message
