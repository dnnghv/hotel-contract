from __future__ import annotations

import json
from typing import List, Literal

import asyncio
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Chunk
from .config import get_openai_key
from . import storage
import logging
logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.openai_key = get_openai_key()
        self.model = "gpt-4o-mini"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def extract(self, chunks: List[Chunk], mode: Literal["base", "addendum"], source_file: str):
        sys_prompt = (
            "Bạn là trình trích xuất. Đầu vào là markdown giữ bảng/heading. "
            "Trả về duy nhất JSON đúng schema. Không suy đoán; thiếu → null + missing_reason. "
            "Mode BASE: trả object gồm keys: meta, clauses. Meta gồm hotel, sign_date (YYYY-MM-DD), currency. "
            "Mode ADDENDUM: trả ChangeSet."
        )
        user_prompt = self._build_user_prompt(chunks, mode)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "top_p": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.openai_key}"}

        def _post():
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            )
            r.raise_for_status()
            return r

        logger.info("LLM request: mode=%s model=%s chunks=%s file=%s", mode, self.model, len(chunks), source_file)
        try:
            r = await asyncio.to_thread(_post)
        except Exception:
            logger.exception("LLM request failed")
            raise
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        # Save raw content for debugging/traceability
        try:
            storage.save_llm_output(source_file=source_file, mode=mode, content=content)
        except Exception:
            logger.warning("Failed to save LLM raw output", exc_info=True)
        try:
            parsed = json.loads(content)
        except Exception:
            logger.exception("LLM JSON parse failed: content preview=%s", content[:200])
            raise
        logger.info("LLM response keys: %s", list(parsed.keys()))
        return parsed

    def _build_user_prompt(self, chunks: List[Chunk], mode: str) -> str:
        header = (
            "Mode: BASE → trả JSON: {\"meta\": {hotel, sign_date, currency}, \"clauses\": [...] } theo schema; "
            "Mode: ADDENDUM → trả ChangeSet theo schema. Ngày YYYY-MM-DD."
        )
        body = "\n\n".join([f"[Chunk]\n{c.markdown}" for c in chunks])
        return f"{header}\n\n{body}" 