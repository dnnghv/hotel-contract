from __future__ import annotations

import json
import os
from datetime import date
from typing import List, Dict, Any

from jsonschema import Draft202012Validator

from .models import BaseContract, Clause, ChangeSet


def _load_schema(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


BASE_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas", "base_contract.schema.json")
CHANGESET_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas", "changeset.schema.json")


base_validator = Draft202012Validator(_load_schema(BASE_SCHEMA_PATH))
changeset_validator = Draft202012Validator(_load_schema(CHANGESET_SCHEMA_PATH))


class ValidationError(Exception):
    pass


def validate_base_contract(bc: BaseContract):
    errors = sorted(base_validator.iter_errors(bc.model_dump(mode="json")), key=lambda e: e.path)
    if errors:
        raise ValidationError("; ".join([e.message for e in errors]))
    for c in bc.clauses:
        _validate_clause_business(c)


def validate_changeset(cs: ChangeSet):
    errors = sorted(changeset_validator.iter_errors(cs.model_dump(mode="json")), key=lambda e: e.path)
    if errors:
        raise ValidationError("; ".join([e.message for e in errors]))
    # simple business checks
    for ch in cs.changes:
        if ch.type.name == "RateAdjustment":
            if ch.payload is None or float(ch.payload.get("rate", 0)) <= 0:
                raise ValidationError("RateAdjustment requires payload.rate > 0")
        if ch.payload and "discount_pct" in ch.payload:
            dp = float(ch.payload["discount_pct"])  # may be nested rule but this is simple guard
            if dp < 0 or dp > 100:
                raise ValidationError("discount_pct must be between 0 and 100")


def _validate_clause_business(c: Clause):
    if c.type.name == "Pricing":
        if c.table:
            for row in c.table:
                if row.rate <= 0:
                    raise ValidationError("rate must be > 0")
                if not row.currency:
                    raise ValidationError("currency required")
        if c.season:
            for sw in c.season:
                if sw.from_ > sw.to:
                    raise ValidationError("season window reversed")
    if c.effective_to and c.effective_to < c.effective_from:
        raise ValidationError("effective_to earlier than effective_from")


def auto_repair_json(doc: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """Best-effort repair of extracted JSON to satisfy minimum schema.

    - base: ensure meta keys and required clause fields exist with sensible defaults
    - addendum: ensure changes array exists (light repair)
    """
    if kind == "base":
        # meta defaults
        meta = doc.get("meta") or {}
        if not meta.get("hotel"):
            meta["hotel"] = "Unknown Hotel"
        if not meta.get("sign_date"):
            meta["sign_date"] = date.today().isoformat()
        if not meta.get("currency"):
            meta["currency"] = "VND"
        doc["meta"] = meta

        # clauses defaults
        clauses = doc.get("clauses") or []
        repaired: List[Dict[str, Any]] = []
        default_from = meta.get("sign_date") or date.today().isoformat()
        for idx, c in enumerate(clauses):
            c = dict(c or {})
            if not c.get("id"):
                c["id"] = f"c{idx+1}"
            if not c.get("type"):
                c["type"] = "Other"
            if not c.get("title"):
                c["title"] = f"Clause {idx+1}"
            if not c.get("effective_from"):
                c["effective_from"] = default_from
            if c.get("confidence") is None:
                c["confidence"] = 0.5
            repaired.append(c)
        doc["clauses"] = repaired
    elif kind == "addendum":
        doc.setdefault("changes", [])
    return doc