from __future__ import annotations

from typing import Optional

from .services import (
    DoclingService,
    SegmentationService,
    ExtractionService,
    ValidationService,
    MergeService,
    RenderService,
    VersioningService,
)
from .models import BaseContract, ChangeSet
import logging
logger = logging.getLogger(__name__)
import asyncio


class ContractPipeline:
    def __init__(
        self,
        docling: Optional[DoclingService] = None,
        segmenter: Optional[SegmentationService] = None,
        extractor: Optional[ExtractionService] = None,
        validator: Optional[ValidationService] = None,
        merger: Optional[MergeService] = None,
        renderer: Optional[RenderService] = None,
        versioning: Optional[VersioningService] = None,
    ):
        self.docling = docling or DoclingService()
        self.segmenter = segmenter or SegmentationService()
        self.extractor = extractor or ExtractionService()
        self.validator = validator or ValidationService()
        self.merger = merger or MergeService()
        self.renderer = renderer or RenderService()
        self.versioning = versioning or VersioningService()

    async def ingest_base(self, filename: str, data: bytes) -> dict:
        logger.info("Pipeline ingest_base start: filename=%s", filename)
        pdf_path = self.versioning.save_pdf(data, filename)
        # pre-assign version for step logging; will persist state later
        contract_id = filename.rsplit(".", 1)[0]
        version = self.versioning.next_version_id(contract_id)
        self.versioning.save_step_text(contract_id, version, "00_input_filename", filename)
        self.versioning.save_step_text(contract_id, version, "01_pdf_path", pdf_path)
        segments = await asyncio.to_thread(self.docling.parse_pdf, pdf_path)
        # save raw markdown of first (and only) segment for traceability
        if segments:
            self.versioning.save_step_text(contract_id, version, "02_docling_markdown", segments[0].raw_md)
        chunks = self.segmenter.segment(segments)
        # save segmented chunks
        self.versioning.save_step_json(contract_id, version, "03_chunks", [c.model_dump(mode="json") for c in chunks])
        extracted = await self.extractor.extract_base(chunks, source_file=pdf_path)
        self.versioning.save_step_json(contract_id, version, "04_llm_extracted_base_raw_repaired", extracted)
        meta = (extracted.get("meta") or {}).copy()
        # đảm bảo có nguồn file trong meta
        meta["source_file"] = filename
        bc = BaseContract(
            contract_id=filename.rsplit(".", 1)[0],
            meta=meta,
            clauses=extracted.get("clauses", []),
        )
        self.versioning.save_step_json(contract_id, version, "05_base_contract_model", bc.model_dump(mode="json"))
        # removed validation step for base contract per requirement
        self.versioning.save_contract_version(bc, version)
        md = self.renderer.to_markdown(bc)
        self.versioning.save_step_text(contract_id, version, "06_render_markdown", md)
        self.versioning.save_render(bc.contract_id, version, md, redline_md="")
        logger.info("Pipeline ingest_base done: contract_id=%s version=%s", bc.contract_id, version)
        return {"contract_id": bc.contract_id, "version": version}

    async def ingest_addendum(self, contract_id: str, filename: str, data: bytes) -> dict:
        logger.info("Pipeline ingest_addendum start: contract_id=%s filename=%s", contract_id, filename)
        latest = self.versioning.latest_version(contract_id)
        if latest is None:
            logger.warning("No base contract found for contract_id=%s", contract_id)
            raise FileNotFoundError("Contract not found")
        base = self.versioning.load_contract_version(contract_id, latest)
        if base is None:
            logger.warning("Base contract version missing: contract_id=%s version=%s", contract_id, latest)
            raise FileNotFoundError("Contract version missing")
        # pre-assign next version for step logging
        version = self.versioning.next_version_id(contract_id)
        self.versioning.save_step_text(contract_id, version, "00_input_filename", filename)
        self.versioning.save_step_json(contract_id, version, "01_loaded_base_version", base.model_dump(mode="json"))
        pdf_path = self.versioning.save_pdf(data, filename)
        self.versioning.save_step_text(contract_id, version, "02_pdf_path", pdf_path)
        segments = await asyncio.to_thread(self.docling.parse_pdf, pdf_path)
        if segments:
            self.versioning.save_step_text(contract_id, version, "03_docling_markdown", segments[0].raw_md)
        chunks = self.segmenter.segment(segments)
        self.versioning.save_step_json(contract_id, version, "04_chunks", [c.model_dump(mode="json") for c in chunks])
        extracted = await self.extractor.extract_addendum(chunks, source_file=pdf_path)
        self.versioning.save_step_json(contract_id, version, "05_llm_extracted_addendum_raw_repaired", extracted)
        cs = ChangeSet(**extracted)
        self.versioning.save_step_json(contract_id, version, "06_changeset_model", cs.model_dump(mode="json"))
        self.validator.validate_changeset(cs)
        new_state = self.merger.merge(base, cs)
        self.versioning.save_step_json(contract_id, version, "07_merged_state", new_state.model_dump(mode="json"))
        self.versioning.save_contract_version(new_state, version)
        md = self.renderer.to_markdown(new_state)
        self.versioning.save_step_text(contract_id, version, "08_render_markdown", md)
        old = self.versioning.load_contract_version(contract_id, version - 1)
        red = self.renderer.to_redline(old, new_state)
        self.versioning.save_step_text(contract_id, version, "09_redline_markdown", red)
        outputs = self.versioning.save_render(contract_id, version, md, redline_md=red)
        logger.info("Pipeline ingest_addendum done: contract_id=%s version=%s", contract_id, version)
        return {"contract_id": contract_id, "version": version, "outputs": outputs}

    def get_state(self, contract_id: str, as_of: Optional[str] = None) -> BaseContract:
        latest = self.versioning.latest_version(contract_id)
        if latest is None:
            raise FileNotFoundError("Contract not found")
        state = self.versioning.load_contract_version(contract_id, latest)
        if state is None:
            raise FileNotFoundError("Contract version missing")
        if as_of:
            from datetime import date
            dt = date.fromisoformat(as_of)
            state = self.versioning.state_as_of(state, dt)
        return state

    def get_redline(self, contract_id: str, version: int) -> str:
        new_state = self.versioning.load_contract_version(contract_id, version)
        if new_state is None:
            raise FileNotFoundError("Version not found")
        old_state = self.versioning.load_contract_version(contract_id, version - 1)
        return self.renderer.to_redline(old_state, new_state) 