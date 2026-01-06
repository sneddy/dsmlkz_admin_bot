# services/hr_assistant_service.py

import json
import logging
from typing import Any, Dict, Optional

from openai import APIStatusError, OpenAI
import tenacity

from configs.config import HR_ASSISTANT_MODEL
from configs.prompts import jd2dict_prompt


class ChatGptHrAssistant:
    """ChatGPT HR Assistant for generating job descriptions in Markdown."""

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 512,
    ):
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model or HR_ASSISTANT_MODEL
        self.client = OpenAI(api_key=api_key)

    def __call__(self, job_description: str) -> str:
        meta = self.text2dict(job_description)
        meta = self.replace_markdown_symbols(meta)
        logging.info("[HR Assistant] Parsed Meta: %s", meta)
        return self.dict2markdown(meta)

    @staticmethod
    def _is_retryable_error(exception: BaseException) -> bool:
        if isinstance(exception, ValueError):
            return True
        if isinstance(exception, APIStatusError):
            return exception.status_code >= 500
        return False

    def text2dict(self, user_jd: str) -> Dict[str, Any]:
        """Returns dictionary with metadata about position."""
        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_attempt(5),
            wait=tenacity.wait_fixed(10),
            retry=tenacity.retry_if_exception(self._is_retryable_error),
            reraise=True,
        ):
            with attempt:
                logging.info(
                    "[HR Assistant] Sending prompt to OpenAI: model=%s attempt=%s text_len=%s",
                    self.model,
                    attempt.retry_state.attempt_number + 1,
                    len(user_jd),
                )
                messages = [
                    {"role": "system", "content": jd2dict_prompt},
                    {"role": "user", "content": user_jd},
                ]
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                )
                content = completion.choices[0].message.content or "{}"
                logging.info(
                    "[HR Assistant] Received response: id=%s prompt_tokens=%s completion_tokens=%s",
                    completion.id,
                    getattr(completion.usage, "prompt_tokens", None),
                    getattr(completion.usage, "completion_tokens", None),
                )
                return self._parse_completion(content)

    @classmethod
    def _parse_completion(cls, content: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response: {exc}") from exc

        normalized = cls._normalize_payload(parsed)
        if not isinstance(normalized, dict):
            raise ValueError("Model response is not a JSON object.")
        cls._prepare_structure(normalized)
        return normalized

    @classmethod
    def _normalize_payload(cls, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {k: cls._normalize_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [cls._normalize_payload(item) for item in payload][:6]
        return cls._normalize_scalar(payload)

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            lowered = stripped.lower()
            if lowered in {"null", "none", ""}:
                return None
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            return stripped
        return value

    @classmethod
    def _prepare_structure(cls, meta: Dict[str, Any]) -> None:
        for nested_key in (
            "location",
            "salary_range",
            "contacts",
            "description",
            "requirements",
        ):
            if not isinstance(meta.get(nested_key), dict):
                meta[nested_key] = {}

        requirements = meta["requirements"]
        if isinstance(requirements, dict):
            for key in ("responsibilities", "required_skills", "optional_skills"):
                value = requirements.get(key)
                if value is None:
                    requirements[key] = []
                elif isinstance(value, list):
                    requirements[key] = value[:6]
                else:
                    requirements[key] = [value]

    @staticmethod
    def _escape_markdown(text):
        if text is None:
            return None
        if text.endswith("."):
            text = text[:-1]
        markdown_chars = r"\`*_{}[]()#+-.!|"
        for char in markdown_chars:
            text = text.replace(char, "\\" + char)
        return text.strip()

    @staticmethod
    def _safe_float(value: Any):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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
        money = meta_dict.get("salary_range") or {}
        if not isinstance(money, dict):
            return None

        currency = (money.get("currency") or "").strip()
        after_taxes = money.get("after_taxes")
        taxes = " NET" if after_taxes else (" Gross" if after_taxes is False else "")
        low = cls._safe_float(money.get("low_limit"))
        high = cls._safe_float(money.get("high_limit"))

        if low is None and high is None:
            return None
        if low is None:
            low = high
        if high is None:
            high = low

        period = f" per {money.get('period')}" if money.get("period") else ""
        if high == low:
            return f"{low:.0f} {currency}{taxes}{period}"
        return f"{low:.0f} to {high:.0f} {currency}{taxes}{period}"

    @classmethod
    def get_location_repr(cls, meta_dict):
        loc = meta_dict.get("location") or {}
        if not isinstance(loc, dict):
            loc = {}
        city = f"{loc.get('city')} \\/ " if loc.get("city") else ""
        remote_flag = loc.get("remote")
        remote = "Remote" if remote_flag else ("Office" if remote_flag is False else "")
        reloc = " \\/ Support Relocation" if loc.get("support_relocation") else ""
        return f"{city}{remote}{reloc}".strip()

    @classmethod
    def dict2markdown(cls, meta: Dict[str, Any]) -> str:
        lines = []

        position_name = meta.get("position_name")
        if position_name:
            lines.append(f"*{position_name}*")

        company_name = meta.get("company_name")
        if company_name:
            clean_name = company_name.replace("\\.", " ")
            lines.append(f"*{clean_name}*")

        money = cls.get_money_repr(meta)
        if money:
            lines.append(f"*{money}*")

        loc = cls.get_location_repr(meta)
        if loc:
            lines.append(f"_{loc}_")

        lines.append("")  # пустая строка после заголовка

        desc = meta.get("description") or {}
        if not isinstance(desc, dict):
            desc = {}
        company_details = desc.get("company_details")
        if company_details:
            lines.append(f"_{company_details}_")

        project_details = desc.get("project_details")
        if project_details:
            lines.append(f"_{project_details}_")

        reqs = meta.get("requirements") or {}
        if not isinstance(reqs, dict):
            reqs = {}
        responsibilities = reqs.get("responsibilities")
        if responsibilities:
            lines.append("\n*Responsibilities*:")
            lines.extend(f"• {r}" for r in responsibilities)

        required_skills = reqs.get("required_skills")
        if required_skills:
            lines.append("\n*Requirements*:")
            lines.extend(f"• {s}" for s in required_skills)

        optional_skills = reqs.get("optional_skills")
        if optional_skills:
            lines.append("\n*Optional*:")
            lines.extend(f"• {s}" for s in optional_skills)

        contact = meta.get("contacts") or {}
        if not isinstance(contact, dict):
            contact = {}
        email = contact.get("email")
        telegram = contact.get("telegram")
        if email or telegram:
            lines.append("\n*Contacts*:")
            if email:
                lines.append(f"📧 {email}")
            if telegram:
                lines.append(f"📱 {telegram}")

        return "\n".join(lines)
