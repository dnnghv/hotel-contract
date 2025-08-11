from __future__ import annotations

import re
from typing import List

from .models import Segment, Chunk


PRICING_KEYS = ["pricing", "rate", "bảng giá", "giá phòng"]
SEASON_KEYS = ["season", "mùa", "giai đoạn"]
POLICY_KEYS = ["cancellation", "no show", "non-refundable", "hoàn", "huỷ"]
STOPSELL_KEYS = ["stop sell", "đóng bán", "ngừng bán"]
PROMO_KEYS = ["promotion", "khuyến mãi", "ưu đãi"]


def guess_label(text: str) -> str | None:
    t = text.lower()
    if any(k in t for k in STOPSELL_KEYS):
        return "StopSell"
    if any(k in t for k in PROMO_KEYS):
        return "Promotion"
    if any(k in t for k in PRICING_KEYS):
        return "Pricing"
    if any(k in t for k in SEASON_KEYS):
        return "Season"
    if any(k in t for k in POLICY_KEYS):
        return "Policy"
    return None


def segment_to_chunks(segments: List[Segment], max_chars: int = 5000) -> List[Chunk]:
    chunks: List[Chunk] = []
    for seg in segments:
        text = seg.raw_md
        # simple split on top-level headings or tables markers
        parts = re.split(r"(?m)^(# .+|<<<TABLE:[^>]+>>>)$", text)
        buffer = ""
        for p in parts:
            if not p:
                continue
            candidate = (buffer + "\n\n" + p).strip() if buffer else p
            if len(candidate) > max_chars and buffer:
                label = guess_label(buffer)
                chunks.append(Chunk(label=label, markdown=buffer, page_range=seg.page_range, source_heading=seg.heading))
                buffer = p
            else:
                buffer = candidate
        if buffer:
            label = guess_label(buffer)
            chunks.append(Chunk(label=label, markdown=buffer, page_range=seg.page_range, source_heading=seg.heading))
    return chunks 