from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import get_db_connection

router = APIRouter(tags=["Stats"])

@router.get("/api/stats")
@router.get("/api/stats/")
@router.get("/api/v1/stats")
@router.get("/api/v1/stats/")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. User activity stats
    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    row = cursor.fetchone()
    
    # 2. Real Feeds count (active feeds followed by user)
    cursor.execute("SELECT COUNT(*) as cnt FROM feeds")
    feeds_cnt_row = cursor.fetchone()
    followed_feeds_count = feeds_cnt_row["cnt"] if feeds_cnt_row else 0

    # 3. Real Articles volume
    cursor.execute("SELECT COUNT(*) as cnt FROM articles")
    articles_cnt_row = cursor.fetchone()
    total_articles_count = articles_cnt_row["cnt"] if articles_cnt_row else 0

    # 4. Ingestion Breakdown (RSS vs Webhook / Mailhook / OCR)
    cursor.execute('''
        SELECT 
            CASE 
                WHEN f.url = 'webhook_feed' OR f.category = 'Webhook' THEN 'Webhook / OCR'
                ELSE 'RSS'
            END as source_type,
            COUNT(a.id) as article_count
        FROM articles a
        LEFT JOIN feeds f ON a.feed_id = f.id
        GROUP BY source_type
    ''')
    ingestion_rows = cursor.fetchall()
    ingestion_sources = {r["source_type"]: r["article_count"] for r in ingestion_rows}

    # 5. Podcasts generated count & podcasts duration
    cursor.execute("SELECT COUNT(*) as cnt FROM podcasts")
    pod_row = cursor.fetchone()
    podcasts_count = pod_row["cnt"] if pod_row else 0

    # 6. Token usage summary (Mistral & Gemini)
    cursor.execute('''
        SELECT usage_type, provider, COUNT(*) as call_count, SUM(tokens_in) as tokens_in, SUM(tokens_out) as tokens_out, SUM(cost_eur) as cost_eur
        FROM token_usage
        GROUP BY usage_type, provider
    ''')
    token_rows = cursor.fetchall()
    conn.close()

    listening_sec = row["listening_seconds"] if row else 0
    articles_read = row["articles_read_count"] if row else 0
    articles_listened = row["articles_listened_count"] if row else 0

    return {
        "listening_seconds": listening_sec,
        "listeningTimeMinutes": round(listening_sec / 60),
        "articles_read_count": articles_read,
        "articlesRead": articles_read,
        "articles_listened_count": articles_listened,
        "articlesListened": articles_listened,
        "podcasts_generated_count": max(podcasts_count, row["podcasts_generated_count"] if row else 0),
        "followed_feeds_count": followed_feeds_count,
        "followedFeedsCount": followed_feeds_count,
        "total_articles_count": total_articles_count,
        "ingestion_sources": ingestion_sources,
        "last_activity": row["last_activity"] if row else None,
        "token_usage": [
            {
                "usage_type": tr["usage_type"],
                "provider": tr["provider"],
                "call_count": tr["call_count"],
                "tokens_in": tr["tokens_in"] or 0,
                "tokens_out": tr["tokens_out"] or 0,
                "cost_eur": tr["cost_eur"] or 0.0
            }
            for tr in token_rows
        ]
    }

class TrackRequest(BaseModel):
    action: str
    amount: int

@router.post("/api/stats/track")
@router.post("/api/stats/track/")
@router.post("/api/v1/stats/track")
@router.post("/track")
def track_stat(payload: TrackRequest):
    valid_actions = {
        "listen_seconds": "listening_seconds",
        "read_article": "articles_read_count",
        "listen_article": "articles_listened_count",
        "generate_podcast": "podcasts_generated_count"
    }
    
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail="Action invalide.")
        
    column = valid_actions[payload.action]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        UPDATE user_stats 
        SET {column} = {column} + ?, last_activity = CURRENT_TIMESTAMP 
        WHERE id = 1
    ''', (payload.amount,))
    conn.commit()
    conn.close()
    
    return {"success": True}

class TokenTrackRequest(BaseModel):
    usage_type: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_eur: float

@router.post("/track_tokens")
def track_tokens(payload: TokenTrackRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    import datetime
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
        INSERT INTO token_usage (date, usage_type, provider, tokens_in, tokens_out, cost_eur)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date_str, payload.usage_type, payload.provider, payload.tokens_in, payload.tokens_out, payload.cost_eur))
    
    conn.commit()
    conn.close()
    return {"success": True}
