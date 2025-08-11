from __future__ import annotations

from typing import List

from .models import BaseContract, Clause, RateRow


def render_markdown(contract: BaseContract) -> str:
    lines: List[str] = []
    m = contract.meta
    lines.append(f"# Contract {contract.contract_id}")
    lines.append("")
    lines.append(f"Hotel: {m.hotel} | Sign date: {m.sign_date} | Currency: {m.currency}")
    lines.append("")
    for c in contract.clauses:
        lines.append(f"## {c.type.value}: {c.title}")
        if c.scope:
            lines.append(f"- Scope: `{c.scope}`")
        lines.append(f"- Effective: {c.effective_from} → {c.effective_to or 'open'}")
        if c.table:
            lines.append("")
            lines.append("| date_from | date_to | rate | currency | notes |")
            lines.append("|-----------|---------|------|----------|-------|")
            for r in c.table:
                if isinstance(r, RateRow):
                    lines.append(f"| {r.date_from} | {r.date_to} | {r.rate} | {r.currency} | {r.notes or ''} |")
                else:
                    lines.append(f"| {r['date_from']} | {r['date_to']} | {r['rate']} | {r['currency']} | {r.get('notes') or ''} |")
            lines.append("")
        if c.policy:
            lines.append(f"- Policy: `{c.policy}`")
        if c.blackout:
            lines.append(f"- Blackout: {c.blackout}")
        if c.season:
            season_str = ", ".join([f"{s.from_}..{s.to}" for s in c.season])
            lines.append(f"- Season: {season_str}")
        if c.text:
            lines.append("")
            lines.append("> " + c.text.replace("\n", "\n> "))
        lines.append("")
    return "\n".join(lines)


def redline(old: BaseContract | None, new: BaseContract) -> str:
    old_ids = {c.id for c in (old.clauses if old else [])}
    new_ids = {c.id for c in new.clauses}
    added = new_ids - (old_ids if old else set())
    removed = (old_ids if old else set()) - new_ids
    lines: List[str] = ["# Redline", ""]
    for c in new.clauses:
        if c.id in added:
            lines.append(f"+ ADD {c.id} {c.type.value} {c.title} {c.effective_from}→{c.effective_to or 'open'}")
    if old:
        for c in old.clauses:
            if c.id in removed:
                lines.append(f"- REMOVE {c.id} {c.type.value} {c.title} {c.effective_from}→{c.effective_to or 'open'}")
    lines.append("")
    return "\n".join(lines) 