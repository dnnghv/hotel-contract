from __future__ import annotations

import os
import json
from datetime import date, datetime
from typing import Optional

from pydantic import TypeAdapter

from .models import BaseContract, ChangeSet


DATA_DIR = os.getenv("DATA_DIR", "/home/ebk/AI.ROVI/Contract Test/data")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "contracts"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "docs"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "versions"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "renders"), exist_ok=True)


def save_pdf(doc_bytes: bytes, filename: str) -> str:
    _ensure_dirs()
    path = os.path.join(DATA_DIR, "docs", filename)
    with open(path, "wb") as f:
        f.write(doc_bytes)
    return path


def next_version_id(contract_id: str) -> int:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "versions", contract_id)
    os.makedirs(base, exist_ok=True)
    existing = [int(p.split(".")[0]) for p in os.listdir(base) if p.endswith(".json")]
    return max(existing or [0]) + 1


def save_contract_version(contract: BaseContract, version: int) -> str:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "versions", contract.contract_id)
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{version}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(contract.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)
    return path


def load_contract_version(contract_id: str, version: int) -> Optional[BaseContract]:
    path = os.path.join(DATA_DIR, "versions", contract_id, f"{version}.json")
    if not os.path.exists(path):
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
    return BaseContract(contract_id=contract.contract_id, meta=contract.meta, clauses=filtered)


def save_render(contract_id: str, version: int, content_md: str, redline_md: str | None = None) -> dict:
    _ensure_dirs()
    base = os.path.join(DATA_DIR, "renders", contract_id)
    os.makedirs(base, exist_ok=True)
    out_md = os.path.join(base, f"v{version}.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(content_md)
    out_red = None
    if redline_md:
        out_red = os.path.join(base, f"v{version}_redline.md")
        with open(out_red, "w", encoding="utf-8") as f:
            f.write(redline_md)
    return {"markdown": out_md, "redline": out_red} 