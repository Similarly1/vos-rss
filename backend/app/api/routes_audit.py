from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
from app.database import get_db_connection
from app.services.audit import run_feed_health_audit, clean_inactive_feeds, get_categories_balance_audit, toggle_ignore_audit_category

router = APIRouter(prefix="/api/audit", tags=["audit"])

class CleanInactiveRequest(BaseModel):
    feed_ids: List[int]

class IgnoreCategoryRequest(BaseModel):
    category: str
    ignore: bool

@router.get("/health-check")
def health_check():
    try:
        return run_feed_health_audit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories-balance")
def categories_balance():
    try:
        return get_categories_balance_audit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ignore-category")
def ignore_category(request: IgnoreCategoryRequest):
    try:
        ignored_list = toggle_ignore_audit_category(request.category, request.ignore)
        return {"ignored_categories": ignored_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean-inactive")
def clean_inactive(request: CleanInactiveRequest):
    try:
        deleted = clean_inactive_feeds(request.feed_ids)
        return {"deleted_count": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
