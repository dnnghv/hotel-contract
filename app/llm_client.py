from __future__ import annotations

import json
from typing import List, Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Chunk
from .config import get_openai_key


class LLMClient:
    def __init__(self):
        self.openai_key = get_openai_key()
        self.model = "gpt-4o-mini"

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def extract(self, chunks: List[Chunk], mode: Literal["base", "addendum"], source_file: str):
        sys_prompt = (
            "Bạn là trình trích xuất. Đầu vào là markdown giữ bảng/heading. "
            "Trả về duy nhất JSON đúng schema. Không suy đoán; thiếu → null + missing_reason."
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
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _build_user_prompt(self, chunks: List[Chunk], mode: str) -> str:
        header = (
            "Mode: BASE → trả mảng clauses[] theo schema BaseContract.clauses; "
            "Mode: ADDENDUM → trả ChangeSet theo schema. Ngày YYYY-MM-DD."
        )
        body = "\n\n".join([f"[Chunk]\n{c.markdown}" for c in chunks])
        return f"{header}\n\n{body}" 