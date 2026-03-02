
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from app.intelligent_ranker import rank_resumes
from app.logger import logger


app = FastAPI(title="AI Resume Screening API")

# Request schema
class ResumeRequest(BaseModel):
    job_description: str
    resumes: List[str]
    resume_names: List[str]

@app.get("/health")
def health():
    return {"status": "API running 🚀"}

@app.post("/rank")
def rank(request: ResumeRequest):

    try:
        logger.info("Ranking request received")

        results = rank_resumes(
            request.resumes,
            request.resume_names,
            request.job_description
        )

        return {
            "total_candidates": len(results),
            "ranking": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




