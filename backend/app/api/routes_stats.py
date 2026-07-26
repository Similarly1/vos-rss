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
    conn.close()
    if not row:
        return {
            "listening_seconds": 0,
            "articles_read_count": 0,
            "articles_listened_count": 0,
            "podcasts_generated_count": 0,
            "last_activity": None
        }
    return dict(row)

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
