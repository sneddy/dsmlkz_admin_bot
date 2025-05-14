# services/hr_assistant_service.py

import ast
import functools
import logging
from typing import Any, Dict

import numpy as np
import openai
import tenacity

from configs.prompts import jd2dict_prompt


class ChatGptHrAssistant:
    """ChatGPT HR Assistant for generating job descriptions in Markdown."""
    def __init__(self, api_key: str, temperature: float = 0.75):
        self.api_key = api_key
        self.temperature = temperature
        openai.api_key = api_key
        self.completion = functools.partial(openai.ChatCompletion.create,
                                            model='gpt-3.5-turbo',
                                            temperature=self.temperature)

    def __call__(self, job_description: str) -> str:
        meta = self.text2dict(job_description)
        meta = self.replace_markdown_symbols(meta)
        logging.info(f"[HR Assistant] Parsed Meta: {meta}")
        return self.dict2markdown(meta)

    def text2dict(self, user_jd: str) -> Dict[str, str]:
        """Returns dictionary with metadata about position."""
        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_attempt(5),
            wait=tenacity.wait_fixed(10),
            retry=tenacity.retry_if_exception_type((ValueError, openai.error.ServiceUnavailableError)),
            reraise=True,
        ):
            with attempt:
                messages = [
                    {'role': 'system', 'content': jd2dict_prompt},
                    {'role': 'user', 'content': user_jd}
                ]
                answer = self.completion(messages=messages)['choices'][0]['message']['content']
                return ast.literal_eval(answer)

    @staticmethod
    def _escape_markdown(text):
        if text is None:
            return None
        if text.endswith('.'):
            text = text[:-1]
        markdown_chars = r"\`*_{}[]()#+-.!|"
        for char in markdown_chars:
            text = text.replace(char, "\\" + char)
        return text.strip()

    @classmethod
    def replace_markdown_symbols(cls, meta_dict):
        new_dict = {}
        for k, v in meta_dict.items():
            if isinstance(v, str):
                new_dict[k] = cls._escape_markdown(v)
            elif isinstance(v, dict):
                new_dict[k] = cls.replace_markdown_symbols(v)
            elif isinstance(v, list):
                new_dict[k] = [cls._escape_markdown(item) for item in v]
            else:
                new_dict[k] = v
        return new_dict

    @classmethod
    def get_money_repr(cls, meta_dict):
        money = meta_dict.get("salary_range", {})
        if money:
            currency = money.get('currency', "")
            after_taxes = money.get('after_taxes')
            taxes = " NET" if after_taxes else (" Gross" if after_taxes is False else "")
            low = money.get('low_limit', 0)
            high = money.get('high_limit', np.inf)
            period = f" per {money.get('period')}" if money.get('period') else ""
            return f"{low:.0f} to {high:.0f} {currency}{taxes}{period}"

    @classmethod
    def get_location_repr(cls, meta_dict):
        loc = meta_dict.get("location", {})
        city = f"{loc.get('city')} \\/ " if loc.get("city") else ""
        remote = "Remote" if loc.get("remote") else "Office"
        reloc = " \\/ Support Relocation" if loc.get("support_relocation") else ""
        return f"{city}{remote}{reloc}"

    @classmethod
    def dict2markdown(cls, meta: Dict[str, Any]) -> str:
        lines = []

        if meta.get('position_name'):
            lines.append(f"*{meta['position_name']}*")

        if meta.get('company_name'):
            lines.append(f"*{meta['company_name'].replace('\\.', ' ')}*")

        if money := cls.get_money_repr(meta):
            lines.append(f"*{money}*")

        if loc := cls.get_location_repr(meta):
            lines.append(f"_{loc}_")

        lines.append("")
        desc = meta.get("description", {})
        if desc.get("company_details"):
            lines.append(f"_{desc['company_details']}_")
        if desc.get("project_details"):
            lines.append(f"_{desc['project_details']}_")

        reqs = meta.get("requirements", {})
        if resp := reqs.get("responsibilities"):
            lines.append("\n*Responsibilities*:")
            lines.extend(f"• {r}" for r in resp)

        if skills := reqs.get("required_skills"):
            lines.append("\n*Requirements*:")
            lines.extend(f"• {s}" for s in skills)

        if opt := reqs.get("optional_skills"):
            lines.append("\n*Optional*:")
            lines.extend(f"• {s}" for s in opt)

        if contact := meta.get("contacts", {}):
            lines.append("\n*Contacts*:")
            if email := contact.get("email"):
                lines.append(f"📧 {email}")
            if tg := contact.get("telegram"):
                lines.append(f"📱 {tg}")

        return "\n".join(lines)
