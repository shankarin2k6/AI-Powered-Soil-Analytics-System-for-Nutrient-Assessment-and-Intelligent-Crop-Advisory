"""Soil Analytics API. Run from the backend folder:  uvicorn app.main:app --reload

To add a feature (for example the recommendation endpoints in Milestone 3): write a router in app/api/ and add one
include_router line below.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, auth, fields, history, images, soil_tests, trend
from app.config import settings
from app.ingestion.validate import IngestError

settings.check_production_ready()

app = FastAPI(title="Soil Analytics API", version="0.3.0")

# allow_credentials lets the browser send the login cookie to the API; origins must be listed explicitly.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

API_PREFIX = "/api/v1"
for module in (auth, fields, images, soil_tests, history, analysis, trend):
    app.include_router(module.router, prefix=API_PREFIX)


@app.exception_handler(IngestError)
def ingest_error_handler(_request: Request, exc: IngestError):
    """Bad uploads return a readable message plus a message_key the frontend can translate."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "message_key": exc.key})


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
