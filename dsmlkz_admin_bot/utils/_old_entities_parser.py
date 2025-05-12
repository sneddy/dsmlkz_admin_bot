import html
from dataclasses import dataclass
from typing import List


@dataclass
class MessageEntity:
    type: str
    offset: int
    length: int
    url: str = None


class EntitiesParser:
    def __init__(self, raw_text: str, entities: List[MessageEntity]):
        self.raw_text = raw_text
        self.entities = entities
        self._html = None
        self._tg_preview = None
        self._entity_debug = None

    @property
    def html(self) -> str:
        if self._html is None:
            self._html = self._build_html()
        return self._html

    @property
    def tg_preview(self) -> str:
        if self._tg_preview is None:
            self._tg_preview = f"<pre>{html.escape(self.html)}</pre>"
        return self._tg_preview

    @property
    def entity_debug(self) -> str:
        if self._entity_debug is None:
            lines = [
                f"type={e.type}, offset={e.offset}, length={e.length}"
                + (f", url={e.url}" if e.url else "")
                for e in self.entities
            ]
            self._entity_debug = "\n".join(lines)
        return self._entity_debug

    def _build_html(self) -> str:
        # Telegram offset/length are in UTF-16 code units, need to convert to Python string indices
        utf16_to_py = self._utf16_to_python_indices(self.raw_text)

        # Annotate open/close tags
        opens = {}
        closes = {}

        for e in self.entities:
            start = utf16_to_py.get(e.offset)
            end = utf16_to_py.get(e.offset + e.length)
            if start is None or end is None:
                continue

            tag = self._html_tag(e)
            if not tag:
                continue

            opens.setdefault(start, []).append((tag, e))
            closes.setdefault(end, []).append((tag, e))

        # Build final HTML
        result = []
        open_stack = []

        for i, ch in enumerate(self.raw_text):
            if i in closes:
                for tag, _ in reversed(closes[i]):
                    while open_stack:
                        last_tag, _ = open_stack.pop()
                        result.append(f"</{last_tag}>")
                        if last_tag == tag:
                            break

            if i in opens:
                for tag, ent in opens[i]:
                    if tag == "a":
                        result.append(f'<a href="{html.escape(ent.url)}">')
                    else:
                        result.append(f"<{tag}>")
                    open_stack.append((tag, ent))

            result.append(html.escape(ch))

        # Close any remaining tags
        while open_stack:
            tag, _ = open_stack.pop()
            result.append(f"</{tag}>")

        return "".join(result)

    def _html_tag(self, entity: MessageEntity) -> str:
        return {
            "bold": "b",
            "italic": "i",
            "underline": "u",
            "strikethrough": "s",
            "code": "code",
            "pre": "pre",
            "text_link": "a",
            "url": "a",
        }.get(entity.type)

    def _utf16_to_python_indices(self, text: str) -> dict:
        """Convert UTF-16 code unit indices to Python string indices."""
        mapping = {}
        utf16_len = 0
        for i, ch in enumerate(text):
            mapping[utf16_len] = i
            utf16_len += 2 if ord(ch) > 0xFFFF else 1
        mapping[utf16_len] = len(text)  # End of string
        return mapping
