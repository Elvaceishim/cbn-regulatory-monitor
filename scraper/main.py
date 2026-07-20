"""
CBN Monitor API — wraps the Playwright scraper as a FastAPI service.

Same architecture decision as Projects 1 and 2: n8n's Execute Command
node is disabled by default in current versions (a real thing we hit
building the job search pipeline), so scraping logic lives in its own
service that n8n calls over HTTP instead.

This service is stateless — it returns everything currently listed on
the CBN pages every time it's called. It does NOT track what's new;
that's Postgres's job via the n8n pipeline (ON CONFLICT DO NOTHING on
a unique URL constraint), same dedup pattern as the other two projects.

Run standalone for local testing:
    uvicorn main:app --reload --port 8004
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scraper import check_for_updates

app = FastAPI(title="CBN Monitor API")


class Item(BaseModel):
    title: str
    url: str
    sources: list[str]


class CheckResponse(BaseModel):
    checked_at: str
    total_found: int
    items: list[Item]


@app.get("/check", response_model=CheckResponse)
def check():
    try:
        result = check_for_updates()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")
    return CheckResponse(**result)


@app.get("/health")
def health():
    return {"status": "ok"}
