from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from app.structure import structure

app = FastAPI(title="Structured_Job_Posting_Extraction_API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StructureRequest(BaseModel):
    job_description: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/structure")
async def structure_endpoint(payload: StructureRequest) -> dict:
    """Accept a job description and return the structured result from the structure function."""
    return structure(payload.job_description)
