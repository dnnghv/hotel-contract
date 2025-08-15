from __future__ import annotations

import os
import json
from typing import List, Dict, Any

import requests

from .models import Segment
from .config import get_docling_url
import logging
logger = logging.getLogger(__name__)
from pathlib import Path


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
            "ocr_lang": ["en", "vi"],
            "pdf_backend": "dlparse_v2",
            "table_mode": "accurate",
            "abort_on_error": False,
            "include_images": False,
        }

    def parse_pdf(self, file_path: str) -> List[Segment]:
        # MOCK MODE: skip actual HTTP call to Docling and return a synthetic markdown
        # logger.warning("DoclingClient MOCK mode enabled. Skipping HTTP call. file=%s", file_path)
        # # Read mock markdown strictly from app/file.txt
        # app_dir = Path(__file__).resolve().parent
        # mock_path = app_dir / "file.txt"
        # try:
        #     text = mock_path.read_text(encoding="utf-8")
        #     logger.info("Loaded mock markdown from %s (%s chars)", mock_path, len(text))
        # except Exception as e:
        #     logger.warning("Failed reading %s: %s. Falling back to placeholder.", mock_path, e)
        #     text = "# Placeholder\nNo mock content available."
        # return [Segment(page_range=[], heading=None, raw_md=text, table_blocks=[])]
        # --- Real Docling HTTP call ---
        params = self._default_params()

        try:
            with open(file_path, "rb") as fh:
                files = {"files": (os.path.basename(file_path), fh, "application/pdf")}
                logger.info("Docling request: url=%s file=%s", self.endpoint_url, file_path)
                r = requests.post(self.endpoint_url, data=params, files=files,timeout=120)
                r.raise_for_status()


            resp_json = r.json()
            if isinstance(resp_json, dict):
                text = resp_json.get("text") or resp_json.get("content") or resp_json.get("result") or ""
                if isinstance(text, list):
                    text = "\n".join(str(x) for x in text)
                if not isinstance(text, str):
                    text = json.dumps(resp_json, ensure_ascii=False)
            else:
                text = json.dumps(resp_json, ensure_ascii=False)

            logger.info("Docling response: %s", text)
        except Exception as e:
            logger.exception("Docling connection failed")
            raise e

        text = r.text
        logger.info("Docling response length: %s chars", len(text or ""))
        return [Segment(page_range=[], heading=None, raw_md=text or "", table_blocks=[])]
