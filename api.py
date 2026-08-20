from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.intelligent_ranker import rank_texts
from app.logger import logger

app = FastAPI(title="AI Resume Screening API")


class ResumeRequest(BaseModel):
    job_description: str = Field(..., min_length=1)
    resumes: List[str]
    resume_names: List[str]

    @model_validator(mode="after")
    def check_lengths_match(self):
        if len(self.resumes) != len(self.resume_names):
            raise ValueError(
                f"resumes ({len(self.resumes)}) and resume_names "
                f"({len(self.resume_names)}) must be the same length"
            )
        return self


@app.get("/health")
def health():
    return {"status": "API running"}


@app.post("/rank")
def rank(request: ResumeRequest):
    logger.info("Ranking request received: %d resume(s)", len(request.resumes))

    try:
        results = rank_texts(
            request.job_description,
            zip(request.resume_names, request.resumes),
        )
    except Exception:
        # Log the traceback server-side; don't hand the client internal detail.
        logger.exception("Ranking failed")
        raise HTTPException(status_code=500, detail="Ranking failed")

    return {
        "total_candidates": len(results),
        "ranking": results,
    }
