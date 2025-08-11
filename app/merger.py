from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

from rapidfuzz import fuzz

from .models import Clause, BaseContract, ChangeSet, ChangeType, RateRow


@dataclass
class MatchResult:
    clause: Clause
    score: float


PRECEDENCE = {
    "StopSell": 0,
    "OpenSell": 1,
    "RateAdjustment": 2,
    "PolicyUpdate": 3,
    "AllotmentUpdate": 3,
    "TaxUpdate": 3,
    "SurchargeUpdate": 3,
    "Promotion": 4,
}


def sort_changes(changes):
    return sorted(
        changes,
        key=lambda c: (c.effective_from, PRECEDENCE.get(c.type.value, 99)),
    )


def scope_signature(scope: Optional[Dict[str, Any]]) -> str:
    if not scope:
        return ""
    parts = [f"{k}:{v}" for k, v in sorted(scope.items())]
    return "|".join(parts).lower()


def match_targets(clauses: List[Clause], target) -> List[Clause]:
    # direct id
    if target.clause_id:
        return [c for c in clauses if c.id == target.clause_id]
    # filter by type first
    candidates = [c for c in clauses if (not target.type or c.type.value == target.type)]
    # score by scope signature similarity
    tgt_sig = scope_signature(target.scope)
    if not tgt_sig:
        return candidates
    results: List[MatchResult] = []
    for c in candidates:
        score = fuzz.token_set_ratio(tgt_sig, scope_signature(c.scope))
        results.append(MatchResult(c, score))
    results.sort(key=lambda x: x.score, reverse=True)
    if not results:
        return []
    top = results[0].score
    # if ambiguity, return all close to top within 5 points
    return [r.clause for r in results if r.score >= top - 5]


def close_old_if_needed(cl: Clause, new_from: date):
    if cl.effective_to is None or cl.effective_to >= new_from:
        cl.effective_to = new_from - timedelta(days=1)


def _get_currency_from_clause(cl: Clause) -> str:
    if not cl.table:
        return "VND"
    first = cl.table[0]
    if isinstance(first, RateRow):
        return first.currency
    return first.get("currency", "VND")


def insert_or_update_base_rate(cl: Clause, payload: Dict[str, Any], eff_from: date, eff_to: Optional[date]):
    # Append a new rate row window as RateRow object
    rate = float(payload.get("rate"))
    currency = payload.get("currency") or _get_currency_from_clause(cl)
    if cl.table is None:
        cl.table = []
    cl.table.append(
        RateRow(
            date_from=eff_from,
            date_to=eff_to or date(9999, 12, 31),
            rate=rate,
            currency=currency,
            notes=payload.get("notes"),
        )
    )


def add_promotion_layer(cl: Clause, payload: Dict[str, Any], eff_from: date, eff_to: Optional[date]):
    if cl.policy is None:
        cl.policy = {}
    promos = cl.policy.get("promotions") or []
    promos.append({"payload": payload, "from": eff_from, "to": eff_to})
    cl.policy["promotions"] = promos


def apply_update(cl: Clause, ch):
    if cl.policy is None:
        cl.policy = {}
    key = ch.type.value
    cl.policy[key] = {"payload": ch.payload, "from": ch.effective_from, "to": ch.effective_to}


def apply_stop_open(clauses: List[Clause], scope: Dict[str, Any] | None, window):
    for c in clauses:
        if c.type.value == "Pricing":
            if scope_signature(scope) in scope_signature(c.scope):
                if c.policy is None:
                    c.policy = {}
                stops = c.policy.get("stop_sell") or []
                stops.append({"from": window[0], "to": window[1]})
                c.policy["stop_sell"] = stops


def normalize(clauses: List[Clause]) -> List[Clause]:
    # sort tables per clause
    for c in clauses:
        if c.table:
            def _key(r):
                if isinstance(r, RateRow):
                    return (r.date_from, r.date_to)
                return (r.get("date_from"), r.get("date_to"))
            c.table = sorted(c.table, key=_key)
    return clauses


def apply_changes(base: BaseContract, cs: ChangeSet) -> BaseContract:
    changes_sorted = sort_changes(cs.changes)
    for ch in changes_sorted:
        targets = match_targets(base.clauses, ch.target)
        if not targets:
            # mark for review: for simplicity, skip
            continue
        if ch.type == ChangeType.RateAdjustment:
            for cl in targets:
                close_old_if_needed(cl, ch.effective_from)
                insert_or_update_base_rate(cl, ch.payload or {}, ch.effective_from, ch.effective_to)
        elif ch.type == ChangeType.Promotion:
            for cl in targets:
                add_promotion_layer(cl, ch.payload or {}, ch.effective_from, ch.effective_to)
        elif ch.type in {ChangeType.PolicyUpdate, ChangeType.AllotmentUpdate, ChangeType.TaxUpdate, ChangeType.SurchargeUpdate}:
            for cl in targets:
                apply_update(cl, ch)
        elif ch.type in {ChangeType.StopSell, ChangeType.OpenSell}:
            apply_stop_open(base.clauses, scope=ch.target.scope, window=[ch.effective_from, ch.effective_to])
        else:
            # unknown type → skip/mark review
            continue
    base.clauses = normalize(base.clauses)
    return base 