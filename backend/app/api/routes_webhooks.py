from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import json
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
import sqlite3
from app.database import get_db_connection
from app.config import settings

router = APIRouter(tags=["Webhooks"])

class WebhookIngestPayload(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None

class WebhookSourceCreate(BaseModel):
    name: str
    token: str
    category: Optional[str] = "Général"
    css_selectors_json: Optional[str] = None

class AnalyzeSamplePayload(BaseModel):
    html: str

def get_webhook_model(cursor) -> str:
    cursor.execute("SELECT value FROM app_settings WHERE key = 'webhook_model'")
    row = cursor.fetchone()
    return row['value'] if row else 'codestral-latest'

def ensure_webhook_feed(cursor) -> int:
    cursor.execute("SELECT id FROM feeds WHERE url = 'webhook_feed'")
    row = cursor.fetchone()
    if row:
        return row['id']
    cursor.execute("INSERT INTO feeds (url, title, category) VALUES ('webhook_feed', 'Webhook Ingest', 'Webhook')")
    return cursor.lastrowid

@router.post("/api/v1/webhooks/ingest")
async def ingest_webhook(payload: WebhookIngestPayload, token: str = Header(..., alias="X-Webhook-Token")):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM webhook_sources WHERE token = ?", (token,))
        source = cursor.fetchone()
        
        if not source:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        css_selectors = {}
        if source['css_selectors_json']:
            try:
                css_selectors = json.loads(source['css_selectors_json'])
            except:
                pass
                
        # Clean content with BeautifulSoup if css selectors exist
        cleaned_content = payload.content or ""
        extracted_title = payload.title or ""
        
        if payload.content and css_selectors:
            soup = BeautifulSoup(payload.content, 'html.parser')
            
            if 'content' in css_selectors:
                content_el = soup.select_one(css_selectors['content'])
                if content_el:
                    cleaned_content = content_el.get_text(separator='\n', strip=True)
                    
            if 'title' in css_selectors and not extracted_title:
                title_el = soup.select_one(css_selectors['title'])
                if title_el:
                    extracted_title = title_el.get_text(strip=True)
                    
        feed_id = ensure_webhook_feed(cursor)
        final_url = payload.url or f"webhook://{token}/{cursor.lastrowid or 0}"
        
        cursor.execute("""
            INSERT INTO articles (feed_id, title, content, url, is_full_text)
            VALUES (?, ?, ?, ?, 1)
        """, (feed_id, extracted_title or "Untitled", cleaned_content, final_url))
        
        conn.commit()
        return {"status": "success", "article_id": cursor.lastrowid}
    finally:
        conn.close()

@router.post("/api/v1/webhooks/analyze-sample")
async def analyze_sample(payload: AnalyzeSamplePayload):
    conn = get_db_connection()
    cursor = conn.cursor()
    model = get_webhook_model(cursor)
    conn.close()
    
    if not settings.mistral_api_key:
        # Dummy response if no API key
        return {
            "blocks": [
                {"id": 1, "type": "title_candidate", "text": "Example Title", "selector": "h1"},
                {"id": 2, "type": "content_candidate", "text": "Example content...", "selector": "div.content"}
            ]
        }
        
    prompt = f"""
    You are an expert web scraper assistant. 
    Analyze the following HTML and extract the main structural blocks that could represent the Title, Body content, or Author of an article.
    For each block, provide:
    - text: A clean, human-readable snippet of the content.
    - selector: A unique CSS selector that accurately targets this element.
    
    Return a JSON object with a 'blocks' array. Each item in the array must have 'id', 'text', and 'selector' fields.
    HTML:
    {payload.html[:5000]}
    """
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.mistral_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content']
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/webhooks/sources")
def create_webhook_source(source: WebhookSourceCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO webhook_sources (name, token, category, css_selectors_json) VALUES (?, ?, ?, ?)",
            (source.name, source.token, source.category, source.css_selectors_json)
        )
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Token already exists")
    finally:
        conn.close()

@router.get("/api/v1/webhooks/sources")
def list_webhook_sources():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM webhook_sources")
        sources = [dict(row) for row in cursor.fetchall()]
        return {"sources": sources}
    finally:
        conn.close()
