"""Module for drawing job descriptions"""

from collections import defaultdict
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from dsmlkz_admin_bot.services.hr_assistant_service import ChatGptHrAssistant


class JobDrawer:
    """class for drawing job description image"""

    def __init__(self, img_path, font_path: str, description_font_path):
        self.img_path = img_path
        self.img = Image.open(img_path)

        self.font_path = font_path
        self.description_font_path = description_font_path
        self.img_size = self.img.size[0]
        self.left_margin_size = 25
        self.yellow_color = (255, 243, 42)
        self.blue_color = (0, 181, 201)
        self.white_color = (255, 255, 255)

    def reset(self):
        """reset drawn image"""
        self.img = Image.open(self.img_path)

    def save(self, output_path: str):
        self.img.save(output_path)

    def draw(self, meta_info: Dict[str, str]):
        self._adaptive_draw(
            meta_info["position_name"],
            top_margin=300,
            max_rows=2,
            color=self.yellow_color,
        )
        self._adaptive_draw(
            meta_info["company_name"],
            top_margin=450,
            default_size=50,
            max_rows=1,
            color=self.blue_color,
        )

        salary_repr = ChatGptHrAssistant.get_money_repr(meta_info)
        location_repr = ChatGptHrAssistant.get_location_repr(meta_info)
        location_repr = location_repr.replace("\/", "")
        self._adaptive_draw(
            salary_repr,
            top_margin=550,
            default_size=45,
            max_rows=1,
            color=self.yellow_color,
        )
        self._adaptive_draw(
            location_repr,
            top_margin=650,
            default_size=35,
            max_rows=1,
            color=self.white_color,
            left_alignement=False,
        )

        description = meta_info.get("description", None)
        if description:
            project_details = description.get("project_details", None)
            if project_details:
                self._adaptive_draw(
                    project_details,
                    top_margin=800,
                    default_size=35,
                    max_rows=4,
                    color=self.blue_color,
                    use_default_font=False,
                )
            else:
                company_details = description.get("company_details", None)
                if company_details:
                    self._adaptive_draw(
                        company_details,
                        top_margin=800,
                        default_size=35,
                        max_rows=4,
                        color=self.blue_color,
                        use_default_font=False,
                    )
        return self.img

    def _adaptive_draw(
        self,
        text,
        top_margin,
        color,
        default_size=70,
        max_rows: int = 1,
        use_default_font=True,
        left_alignement: bool = True,
    ):
        font_size = default_size
        draw = ImageDraw.Draw(self.img)

        while True:
            rows = self._split_by_rows(text, font_size, use_default_font)
            if len(rows) > max_rows:
                font_size -= 5
            else:
                font_path = (
                    self.font_path if use_default_font else self.description_font_path
                )
                font = ImageFont.truetype(font_path, font_size)
                current_text_y = top_margin
                for row in rows:
                    if left_alignement:
                        text_position = (self.left_margin_size, current_text_y)
                    else:
                        text_width = draw.textlength(row, font=font)
                        text_position = (
                            self.img_size - self.left_margin_size - text_width,
                            current_text_y,
                        )

                    draw.text(text_position, row, fill=color, font=font)
                    _, _, _, current_text_y = draw.textbbox(
                        text_position, row, font=font
                    )
                return font_size

    def _split_by_rows(self, text, font_size: int, use_default_font=True) -> List[str]:
        font_path = self.font_path if use_default_font else self.description_font_path
        font = ImageFont.truetype(font_path, font_size)
        draw = ImageDraw.Draw(self.img)
        max_caption_size = self.img_size - 2 * self.left_margin_size
        text_width = draw.textlength(text, font=font)
        if text_width < max_caption_size:
            return [text]
        words = text.split()
        rows = defaultdict(str)
        current_row = 0
        for word in words:
            possible_row = (rows[current_row] + " " + word).strip()
            possible_row_size = draw.textlength(possible_row, font=font)
            if possible_row_size < max_caption_size:
                rows[current_row] = possible_row
            else:
                current_row += 1
                rows[current_row] = word
        return [rows[row_id] for row_id in range(len(rows))]
