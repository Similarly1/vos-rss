from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import get_db_connection

router = APIRouter(prefix="/api/stats", tags=["Stats"])

class TrackRequest(BaseModel):
    action: str
    amount: int

@router.get("")
@router.get("/")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE id = 1")
    row = cursor.fetchone()
    
    # Get token usage summary
    cursor.execute('''
        SELECT usage_type, provider, SUM(tokens_in) as tokens_in, SUM(tokens_out) as tokens_out, SUM(cost_eur) as cost_eur
        FROM token_usage
        GROUP BY usage_type, provider
    ''')
    token_rows = cursor.fetchall()
    conn.close()
    
    stats_data = dict(row) if row else {
        "listening_seconds": 0,
        "articles_read_count": 0,
        "articles_listened_count": 0,
        "podcasts_generated_count": 0,
        "last_activity": None
    }
    
    stats_data["token_usage"] = [dict(tr) for tr in token_rows]
    return stats_data

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
