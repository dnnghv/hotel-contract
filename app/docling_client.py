from __future__ import annotations

import os
import json
from typing import List, Dict, Any

import httpx

from .models import Segment
from .config import get_docling_url


class DoclingClient:
    def __init__(self, endpoint_url: str | None = None):
        self.endpoint_url = endpoint_url or get_docling_url()

    def _default_params(self) -> Dict[str, Any]:
        return {
            "from_formats": ["pdf"],
            "to_formats": ["text"],
            "image_export_mode": "placeholder",
            "do_ocr": True,
            "force_ocr": False,
            "ocr_engine": "easyocr",
            "ocr_lang": ["en"],
            "pdf_backend": "dlparse_v2",
            "table_mode": "accurate",
            "abort_on_error": False,
            "include_images": False,
        }

    async def parse_pdf(self, file_path: str) -> List[Segment]:
        headers = {}
        params = self._default_params()
        data = {k: (json.dumps(v) if isinstance(v, (list, dict, bool)) else v) for k, v in params.items()}
        async with httpx.AsyncClient(timeout=120) as client:
            with open(file_path, "rb") as fh:
                files = {"files": (os.path.basename(file_path), fh, "application/pdf")}
                r = await client.post(self.endpoint_url, headers=headers, data=data, files=files)
            r.raise_for_status()
            try:
                resp_json = r.json()
                if isinstance(resp_json, dict):
                    text = resp_json.get("text") or resp_json.get("content") or resp_json.get("result") or ""
                    if isinstance(text, list):
                        text = "\n".join(str(x) for x in text)
                    if not isinstance(text, str):
                        text = json.dumps(resp_json, ensure_ascii=False)
                else:
                    text = json.dumps(resp_json, ensure_ascii=False)
            except ValueError:
                text = r.text
        return [Segment(page_range=[], heading=None, raw_md=text or "", table_blocks=[])] 