from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .pipeline import ContractPipeline

app = FastAPI(title="Hotel Contract Pipeline (OOP)")

import logging
logger = logging.getLogger(__name__)


def get_pipeline() -> ContractPipeline:
    return ContractPipeline()


@app.get("/health")
async def health_check():
    """Health check endpoint to verify service and configuration readiness.

    Returns a simple JSON with status="ok" if the pipeline can be constructed.

    Returns:
        dict: {"status": "ok"} when healthy.
    Raises:
        HTTPException: 500 if configuration or initialization fails.
    """
    try:
        _ = get_pipeline()
        logger.info("Health check OK")
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Health check failed: %s", e)
        raise HTTPException(status_code=500, detail=f"config_error: {e}")


@app.post("/contracts/base/ingest")
async def ingest_base_contract(file: UploadFile = File(...)):
    """Ingest a base contract PDF and create version 1.

    Args:
        file (UploadFile): PDF file for the base contract.

    Returns:
        dict: {"contract_id": str, "version": int}

    Raises:
        HTTPException: 500 on processing errors.
    """
    content = await file.read()
    logger.info("Ingest base request: filename=%s, bytes=%s", file.filename, len(content))
    try:
        pipe = get_pipeline()
        result = await pipe.ingest_base(file.filename, content)
        logger.info("Ingest base done: contract_id=%s version=%s", result.get("contract_id"), result.get("version"))
    except Exception as e:
        logger.exception("Ingest base failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.post("/contracts/{contract_id}/addenda/ingest")
async def ingest_addendum_document(contract_id: str, file: UploadFile = File(...)):
    """Ingest an addendum PDF and merge its changes into a new version.

    Args:
        contract_id (str): Existing contract identifier.
        file (UploadFile): PDF file of the addendum.

    Returns:
        dict: {"contract_id": str, "version": int, "outputs": {"markdown": str, "redline": Optional[str]}}

    Raises:
        HTTPException: 404 if contract/version not found; 500 on processing errors.
    """
    logger.info("Ingest addendum request: contract_id=%s, filename=%s", contract_id, file.filename)
    content = await file.read()
    try:
        pipe = get_pipeline()
        result = await pipe.ingest_addendum(contract_id, file.filename, content)
        logger.info("Ingest addendum done: contract_id=%s version=%s", result.get("contract_id"), result.get("version"))
    except FileNotFoundError as e:
        logger.warning("Ingest addendum not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Ingest addendum failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.get("/contracts/{contract_id}/state")
async def get_contract_state(contract_id: str, as_of: Optional[date] = None):
    """Get the contract state, optionally as of a specific date.

    Args:
        contract_id (str): Contract identifier.
        as_of (date, optional): Date to filter effective clauses.

    Returns:
        JSONResponse: Contract as JSON.

    Raises:
        HTTPException: 404 if contract not found; 500 on processing errors.
    """
    try:
        pipe = get_pipeline()
        result = pipe.get_state(contract_id, as_of=as_of.isoformat() if as_of else None)
    except FileNotFoundError as e:
        logger.warning("Get state not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Get state failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content=result.model_dump(mode="json"))


@app.get("/contracts/{contract_id}/versions/{version}/redline")
async def get_contract_redline(contract_id: str, version: int):
    """Generate a redline diff between the specified version and the previous one.

    Args:
        contract_id (str): Contract identifier.
        version (int): Version number to compare against (previous version is version-1).

    Returns:
        dict: {"redline": str}

    Raises:
        HTTPException: 404 if version not found; 500 on processing errors.
    """
    try:
        pipe = get_pipeline()
        content = pipe.get_redline(contract_id, version)
    except FileNotFoundError as e:
        logger.warning("Get redline not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Get redline failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"redline": content}