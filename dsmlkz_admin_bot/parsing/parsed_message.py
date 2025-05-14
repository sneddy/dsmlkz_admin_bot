import html
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ParsedMessage:
    meta_information: Dict
    image_url: str
    raw_text: str
    html_text: str  # actually: HTML content
    tg_preview: str  # escaped HTML preview (e.g. <pre>)
    source: str
    other: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "meta_information": self.meta_information,
            "image_url": self.image_url,
            "raw_text": self.raw_text,
            "html_text": self.html_text,
            "other": self.other,
        }

    @staticmethod
    def valid_timestamp(ts):
        return ts if ts else None

    def to_channels_content_dict(self, post_id: str) -> dict:
        return {
            "post_id": post_id,
            "image_url": self.image_url,
            "channel_id": self.meta_information.get("channel_id"),
            "channel_name": self.meta_information.get("channel_name"),
            "message_id": self.meta_information.get("message_id"),
            "created_at": self.valid_timestamp(self.meta_information.get("created_at")),
            "post_link": self.meta_information.get("post_link"),
            "is_public": self.meta_information.get("is_public"),
            "sender_id": self.meta_information.get("sender_id"),
            "sender_name": self.meta_information.get("sender_name"),
            "html_text": self.html_text,
        }

    @property
    def meta_information_html(self) -> str:
        return "".join(
            f"<b>{html.escape(k.replace('_', ' ').capitalize())}:</b> {html.escape(str(v))}\n"
            for k, v in self.meta_information.items()
            if v is not None
        )

    @property
    def other_information_html(self) -> str:
        return "".join(
            f"<b>{html.escape(k.replace('_', ' ').capitalize())}:</b> {html.escape(str(v))}\n"
            for k, v in self.other.items()
            if v is not None
        )

    @property
    def full_text_html(self) -> str:
        image_html = (
            f"<b>Image:</b> {html.escape(self.image_url)}\n" if self.image_url else ""
        )
        sections = [
            self.tg_preview,
            image_html,
            self.meta_information_html,
            self.other_information_html,
        ]
        return "\n".join(filter(None, sections))
