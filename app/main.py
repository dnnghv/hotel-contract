from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .pipeline import ContractPipeline
from .exceptions import ConfigurationError

app = FastAPI(title="Hotel Contract Pipeline (OOP)")


def get_pipeline() -> ContractPipeline:
    # Lazy create to avoid startup crash if env missing
    try:
        return ContractPipeline()
    except Exception as e:
        raise ConfigurationError(str(e))


@app.get("/health")
async def health():
    try:
        _ = get_pipeline()
        return {"status": "ok"}
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"config_error: {e}")


@app.post("/contracts/base:ingest")
async def ingest_base(file: UploadFile = File(...)):
    content = await file.read()
    try:
        pipe = get_pipeline()
        result = await pipe.ingest_base(file.filename, content)
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"config_error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.post("/contracts/{contract_id}/addenda:ingest")
async def ingest_addendum(contract_id: str, file: UploadFile = File(...)):
    content = await file.read()
    try:
        pipe = get_pipeline()
        result = await pipe.ingest_addendum(contract_id, file.filename, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"config_error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@app.get("/contracts/{contract_id}/state")
async def get_state(contract_id: str, as_of: Optional[date] = None):
    try:
        pipe = get_pipeline()
        result = pipe.get_state(contract_id, as_of=as_of.isoformat() if as_of else None)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"config_error: {e}")
    return JSONResponse(content=result.model_dump(mode="json"))


@app.get("/contracts/{contract_id}/versions/{version}/redline")
async def get_redline(contract_id: str, version: int):
    try:
        pipe = get_pipeline()
        content = pipe.get_redline(contract_id, version)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"config_error: {e}")
    return {"redline": content} 