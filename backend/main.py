"""
FastAPI Backend — Entry point for the Monday.com BI Agent.
Exposes REST endpoints that the React frontend calls.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import MONDAY_DEALS_BOARD_ID, MONDAY_WORKORDERS_BOARD_ID
from agent import process_query
from monday_client import get_board_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Monday.com BI Agent backend starting up...")
    yield
    logger.info("Monday.com BI Agent backend shutting down...")


app = FastAPI(
    title="Monday.com BI Agent",
    description="AI-powered business intelligence agent for Monday.com boards",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins during development
# Will be restricted to the Vercel frontend domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    message: str
    history: list[dict] = []


class QueryResponse(BaseModel):
    answer: str
    action_trace: list[str]
    data_quality_report: dict


class HealthResponse(BaseModel):
    status: str
    service: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Process a business intelligence query.
    Accepts a user message and conversation history,
    returns an AI-generated answer with action trace and data quality report.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info(f"Processing query: {request.message[:100]}...")

    try:
        result = process_query(request.message, request.history)
        return QueryResponse(
            answer=result["answer"],
            action_trace=result["action_trace"],
            data_quality_report=result["data_quality_report"],
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}",
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "service": "Monday BI Agent"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify the deployment is alive."""
    return HealthResponse(status="ok", service="monday-bi-agent")


@app.get("/boards/schema")
async def get_schema(board: str):
    """
    Get the live schema for a board.
    Query param 'board' should be "deals" or "workorders".
    """
    board_map = {
        "deals": MONDAY_DEALS_BOARD_ID,
        "workorders": MONDAY_WORKORDERS_BOARD_ID,
    }

    if board not in board_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid board name: '{board}'. Use 'deals' or 'workorders'.",
        )

    try:
        schema = get_board_schema(board_map[board])
        return schema
    except Exception as e:
        logger.error(f"Error fetching schema for {board}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching board schema: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
