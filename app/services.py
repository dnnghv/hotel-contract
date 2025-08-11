from __future__ import annotations

from typing import List, Optional, Dict, Any

from .docling_client import DoclingClient
from .segmenter import segment_to_chunks
from .llm_client import LLMClient
from .models import Segment, Chunk, BaseContract, ChangeSet
from .validator import validate_base_contract, validate_changeset, auto_repair_json
from .merger import apply_changes
from .render import render_markdown, redline
from . import storage


class DoclingService:
    def __init__(self, client: Optional[DoclingClient] = None):
        self.client = client or DoclingClient()

    async def parse_pdf(self, file_path: str) -> List[Segment]:
        return await self.client.parse_pdf(file_path)


class SegmentationService:
    def __init__(self, max_chars: int = 5000):
        self.max_chars = max_chars

    def segment(self, segments: List[Segment]) -> List[Chunk]:
        return segment_to_chunks(segments, max_chars=self.max_chars)


class ExtractionService:
    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def extract_base(self, chunks: List[Chunk], source_file: str) -> Dict[str, Any]:
        data = await self.client.extract(chunks, mode="base", source_file=source_file)
        return auto_repair_json(data, kind="base")

    async def extract_addendum(self, chunks: List[Chunk], source_file: str) -> Dict[str, Any]:
        data = await self.client.extract(chunks, mode="addendum", source_file=source_file)
        return auto_repair_json(data, kind="addendum")


class ValidationService:
    def __init__(self):
        pass

    def validate_base_contract(self, bc: BaseContract) -> None:
        validate_base_contract(bc)

    def validate_changeset(self, cs: ChangeSet) -> None:
        validate_changeset(cs)


class MergeService:
    def __init__(self):
        pass

    def merge(self, base: BaseContract, cs: ChangeSet) -> BaseContract:
        return apply_changes(base, cs)


class RenderService:
    def __init__(self):
        pass

    def to_markdown(self, contract: BaseContract) -> str:
        return render_markdown(contract)

    def to_redline(self, old: Optional[BaseContract], new: BaseContract) -> str:
        return redline(old, new)


class VersioningService:
    def __init__(self):
        pass

    def save_pdf(self, doc_bytes: bytes, filename: str) -> str:
        return storage.save_pdf(doc_bytes, filename)

    def next_version_id(self, contract_id: str) -> int:
        return storage.next_version_id(contract_id)

    def save_contract_version(self, contract: BaseContract, version: int) -> str:
        return storage.save_contract_version(contract, version)

    def load_contract_version(self, contract_id: str, version: int) -> Optional[BaseContract]:
        return storage.load_contract_version(contract_id, version)

    def latest_version(self, contract_id: str) -> Optional[int]:
        return storage.latest_version(contract_id)

    def state_as_of(self, contract: BaseContract, as_of) -> BaseContract:
        return storage.state_as_of(contract, as_of)

    def save_render(self, contract_id: str, version: int, content_md: str, redline_md: Optional[str] = None) -> dict:
        return storage.save_render(contract_id, version, content_md, redline_md) 