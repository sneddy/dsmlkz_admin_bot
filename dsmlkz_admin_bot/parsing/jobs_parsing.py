import re
from aiogram.types import Message
from dsmlkz_admin_bot.parsing.base_parsing import BaseParsing
from dsmlkz_admin_bot.parsing.parsed_message import ParsedMessage


class JobsParsing(BaseParsing):
    def parse(self, message: Message) -> ParsedMessage:
        parsed_message = super().parse(message)

        job_details = self.extract_job_details(parsed_message.raw_text)

        parsed_message = ParsedMessage(
            meta_information=parsed_message.meta_information,
            image_url=parsed_message.image_url,
            raw_text=parsed_message.raw_text,
            html_text=parsed_message.html_text,
            tg_preview=parsed_message.tg_preview,
            other=job_details,
            source="jobs",
        )

        return parsed_message

    def extract_job_details(self, raw_text: str) -> dict:
        lines = raw_text.strip().split("\n")

        # Basic Info Extraction
        position = lines[0].strip() if len(lines) > 0 else ""
        company_name = lines[1].strip() if len(lines) > 1 else ""
        salary_range = lines[2].strip() if len(lines) > 2 else ""
        location = lines[3].strip() if len(lines) > 3 else ""

        description = ""
        responsibilities = []
        requirements = []
        contacts = []

        current_block = None

        for line in lines[4:]:
            line = line.strip()
            if not line:
                continue

            if line.lower().startswith("responsibilities"):
                current_block = "responsibilities"
                continue
            if line.lower().startswith("requirements"):
                current_block = "requirements"
                continue
            if line.lower().startswith("contacts"):
                current_block = "contacts"
                continue

            if current_block == "responsibilities":
                responsibilities.append(line)
            elif current_block == "requirements":
                requirements.append(line)
            elif current_block == "contacts":
                contacts.append(line)
            else:
                description += line + " "

        # Extract email & telegram contacts
        email_matches = re.findall(r"\S+@\S+", raw_text)
        tg_matches = re.findall(r"@\w+", raw_text)

        # Create job-specific data
        job_data = {
            "position": position,
            "company_name": company_name,
            "salary_range": salary_range,
            "location": location,
            "company_description": description.strip(),
            "responsibilities": responsibilities,
            "requirements": requirements,
            "contacts": {"emails": email_matches, "telegram": tg_matches},
        }

        return job_data
