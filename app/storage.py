from __future__ import annotations

import os
import json
from datetime import date, datetime
from typing import Optional

from pydantic import TypeAdapter

from .models import BaseContract, ChangeSet
import logging
logger = logging.getLogger(__name__)
from .config import get_data_dir
import re


DATA_DIR = get_data_dir()


def _ensure_dirs():
    logger.debug("Ensuring data directories under %s", DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "contracts"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "docs"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "versions"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "renders"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "steps"), exist_ok=True)


def save_pdf(doc_bytes: bytes, filename: str) -> str:
    _ensure_dirs()
    path = os.path.join(DATA_DIR, "docs", filename)
    logger.info("Saving PDF: %s", path)
    with open(path, "wb") as f:
        f.write(doc_bytes)
    return path


def next_version_id(contract_id: str) -> int:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "versions", contract_id)
    os.makedirs(base, exist_ok=True)
    existing = [int(p.split(".")[0]) for p in os.listdir(base) if p.endswith(".json")]
    next_v = max(existing or [0]) + 1
    logger.info("Next version id: contract_id=%s -> %s", contract_id, next_v)
    return next_v


def save_contract_version(contract: BaseContract, version: int) -> str:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "versions", contract.contract_id)
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{version}.json")
    logger.info("Saving contract version: %s", path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(contract.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)
    return path


def load_contract_version(contract_id: str, version: int) -> Optional[BaseContract]:
    path = os.path.join(DATA_DIR, "versions", contract_id, f"{version}.json")
    if not os.path.exists(path):
        logger.warning("Version not found: %s", path)
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return TypeAdapter(BaseContract).validate_python(data)


def latest_version(contract_id: str) -> Optional[int]:
    base = os.path.join(DATA_DIR, "versions", contract_id)
    if not os.path.exists(base):
        return None
    versions = [int(p.split(".")[0]) for p in os.listdir(base) if p.endswith(".json")]
    return max(versions) if versions else None


def state_as_of(contract: BaseContract, as_of: date) -> BaseContract:
    # filter clauses by effective window
    filtered = [c for c in contract.clauses if (c.effective_from <= as_of and (c.effective_to is None or c.effective_to >= as_of))]
    logger.info("State as of %s -> %s clauses (from %s)", as_of, len(filtered), len(contract.clauses))
    return BaseContract(contract_id=contract.contract_id, meta=contract.meta, clauses=filtered)


def save_render(contract_id: str, version: int, content_md: str, redline_md: str | None = None) -> dict:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "renders", contract_id)
    os.makedirs(base, exist_ok=True)
    out_md = os.path.join(base, f"v{version}.md")
    logger.info("Saving render markdown: %s", out_md)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(content_md)
    out_red = None
    if redline_md:
        out_red = os.path.join(base, f"v{version}_redline.md")
        logger.info("Saving redline markdown: %s", out_red)
        with open(out_red, "w", encoding="utf-8") as f:
            f.write(redline_md)
    return {"markdown": out_md, "redline": out_red} 


def save_llm_output(source_file: str, mode: str, content: str) -> str:
    """Save raw LLM response content to a txt file under DATA_DIR/llm.

    Args:
        source_file: Original PDF file path used for extraction (for naming).
        mode: "base" or "addendum".
        content: Raw JSON string returned by LLM API.

    Returns:
        Output file path.
    """
    _ensure_dirs()
    out_dir = os.path.join(DATA_DIR, "llm")
    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    out_path = os.path.join(out_dir, f"{base_name}_{mode}.txt")
    logger.info("Saving LLM raw output: %s", out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


def _steps_dir(contract_id: str, version: int) -> str:
    _ensure_dirs()
    path = os.path.join(DATA_DIR, "steps", contract_id, f"v{version}")
    os.makedirs(path, exist_ok=True)
    return path


def _sanitize_step_name(step_name: str) -> str:
    name = step_name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def save_step_text(contract_id: str, version: int, step_name: str, content: str) -> str:
    """Save free-form text content for a pipeline step.

    Files are stored under DATA_DIR/steps/{contract_id}/v{version}/{step_name}.txt
    """
    base = _steps_dir(contract_id, version)
    fname = f"{_sanitize_step_name(step_name)}.txt"
    out_path = os.path.join(base, fname)
    logger.info("Saving step text: %s", out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


def save_step_json(contract_id: str, version: int, step_name: str, obj) -> str:
    """Save JSON-serialized content for a pipeline step as .txt (pretty JSON)."""
    text = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    return save_step_text(contract_id, version, step_name, text)