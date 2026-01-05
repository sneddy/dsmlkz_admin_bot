from functools import cached_property
from typing import List
import html


class MessageEntity:
    def __init__(self, type: str, offset: int, length: int, url: str = None):
        self.type = type
        self.offset = offset
        self.length = length
        self.url = url


class EntitiesParser:
    def __init__(self, raw_text: str, entities: List[MessageEntity]):
        self.raw_text = raw_text
        self.entities = sorted(entities or [], key=lambda e: (e.offset, -e.length))
        self.offset_map = self._build_utf16_to_py_index_map(raw_text)

    def _build_utf16_to_py_index_map(self, s: str) -> dict[int, int]:
        """
        Build a mapping from UTF-16 code unit offsets (Telegram uses) to Python string indices.
        """
        mapping = {}
        utf16_index = 0
        for i, char in enumerate(s):
            mapping[utf16_index] = i
            utf16_index += 2 if ord(char) > 0xFFFF else 1
        return mapping

    def _convert_offset(self, utf16_offset: int) -> int:
        """
        Convert Telegram UTF-16 offset to Python str index.
        If offset is beyond the known map, returns len(self.raw_text).
        """
        return self.offset_map.get(utf16_offset, len(self.raw_text))

    @cached_property
    def html(self) -> str:
        if not self.entities:
            return html.escape(self.raw_text)

        events = []

        for entity in self.entities:
            start = self._convert_offset(entity.offset)
            end = self._convert_offset(entity.offset + entity.length)
            events.append((start, "open", entity))
            events.append((end, "close", entity))

        events.sort(key=lambda e: (e[0], 0 if e[1] == "open" else 1))

        result = []
        current_pos = 0
        open_tags_stack = []

        for pos, event_type, entity in events:
            if current_pos < pos:
                result.append(html.escape(self.raw_text[current_pos:pos]))
                current_pos = pos

            if event_type == "open":
                tag = self._get_open_tag(entity)
                result.append(tag)
                open_tags_stack.append((entity, tag))
            else:  # close
                for i in reversed(range(len(open_tags_stack))):
                    open_entity, open_tag = open_tags_stack[i]
                    if open_entity is entity:
                        close_tag = self._get_close_tag(open_tag)
                        result.append(close_tag)
                        open_tags_stack.pop(i)
                        break

        result.append(html.escape(self.raw_text[current_pos:]))

        while open_tags_stack:
            _, open_tag = open_tags_stack.pop()
            result.append(self._get_close_tag(open_tag))

        return "".join(result)

    @cached_property
    def tg_preview(self) -> str:
        entities_str = "\n".join(
            f"type={e.type}, offset={e.offset}, length={e.length}"
            + (f", url={e.url}" if e.url else "")
            for e in self.entities
        )
        return f"<pre>{html.escape(entities_str)}\n\n{self.html}</pre>"

    def _get_open_tag(self, entity: MessageEntity) -> str:
        if entity.type == "bold":
            return "<b>"
        if entity.type == "italic":
            return "<i>"
        if entity.type == "underline":
            return "<u>"
        if entity.type == "strikethrough":
            return "<s>"
        if entity.type == "code":
            return "<code>"
        if entity.type == "pre":
            return "<pre>"
        if entity.type == "text_link" and entity.url:
            return f'<a href="{html.escape(entity.url)}">'
        return ""

    def _get_close_tag(self, open_tag: str) -> str:
        if open_tag.startswith("<a "):
            return "</a>"
        return open_tag.replace("<", "</")
