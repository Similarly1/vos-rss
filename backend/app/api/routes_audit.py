from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
import sqlite3
from app.database import get_db_connection
from app.services.audit import run_feed_health_audit, clean_inactive_feeds

router = APIRouter(prefix="/api/audit", tags=["audit"])

class CleanInactiveRequest(BaseModel):
    feed_ids: List[int]

def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

@router.get("/health-check")
def health_check(conn: sqlite3.Connection = Depends(get_db)):
    try:
        result = run_feed_health_audit(conn)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean-inactive")
def clean_inactive(request: CleanInactiveRequest, conn: sqlite3.Connection = Depends(get_db)):
    try:
        deleted = clean_inactive_feeds(conn, request.feed_ids)
        return {"deleted_count": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
