from aiogram.types import MessageEntity
from html import escape
from collections import defaultdict


class EntitiesParser:
    def __init__(self, raw_text: str, entities: list[MessageEntity]):
        self.raw_text = raw_text or ""
        self.entities = entities or []
        self.char_map = self._build_char_map(self.raw_text)
        self.html = self._build_html()
        self.tg_preview = f"<pre>{escape(self.html)}</pre>"
        self.entity_debug = self._debug_entities()

    def _build_char_map(self, text: str) -> list[str]:
        # Convert text into a list of characters handling surrogate pairs (emoji-safe)
        return [char for char in text]

    def _utf16_to_index(self, utf16_offset: int) -> int:
        # Map UTF-16 offset to Python string index
        count = 0
        for i, ch in enumerate(self.char_map):
            ch_utf16_len = len(ch.encode("utf-16-le")) // 2
            count += ch_utf16_len
            if count > utf16_offset:
                return i
        return len(self.char_map)

    def _get_tag(self, entity: MessageEntity):
        if entity.type == "bold":
            return "b"
        elif entity.type == "italic":
            return "i"
        elif entity.type == "underline":
            return "u"
        elif entity.type == "strikethrough":
            return "s"
        elif entity.type == "code":
            return "code"
        elif entity.type == "pre":
            return "pre"
        elif entity.type in ("text_link", "url"):
            href = escape(
                entity.url
                or self.raw_text[
                    self._utf16_to_index(entity.offset) : self._utf16_to_index(
                        entity.offset + entity.length
                    )
                ]
            )
            return f'a href="{href}"'
        return None

    def _build_html(self) -> str:
        # Step 1: collect tag insertions
        insert_map = defaultdict(list)

        for entity in self.entities:
            start = self._utf16_to_index(entity.offset)
            end = self._utf16_to_index(entity.offset + entity.length)
            tag = self._get_tag(entity)
            if tag:
                insert_map[start].append(("open", tag))
                insert_map[end].append(("close", tag))

        # Step 2: apply inserts using stack
        result = []
        tag_stack = []

        for i in range(len(self.char_map) + 1):
            if i in insert_map:
                # Close tags first (in reverse order)
                for kind, tag in sorted(insert_map[i], reverse=True):
                    if kind == "close":
                        result.append(f"</{tag.split()[0]}>")
                        if tag_stack and tag_stack[-1] == tag:
                            tag_stack.pop()
                # Open tags (in original order)
                for kind, tag in insert_map[i]:
                    if kind == "open":
                        result.append(f"<{tag}>")
                        tag_stack.append(tag)

            if i < len(self.char_map):
                result.append(escape(self.char_map[i]))

        # Auto-close any unclosed tags (safety net)
        while tag_stack:
            tag = tag_stack.pop()
            result.append(f"</{tag.split()[0]}>")

        return "".join(result)

    def _debug_entities(self) -> str:
        lines = []
        for e in self.entities:
            lines.append(f"type={e.type}, offset={e.offset}, length={e.length}")
        return "\n".join(lines)
