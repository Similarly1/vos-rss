import base64
import hashlib
import json
import re
from typing import List, Dict, Optional

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

from app.config import settings
from app.database import get_db_connection

def get_fernet_key(secret: str) -> bytes:
    hasher = hashlib.sha256()
    hasher.update(secret.encode('utf-8'))
    return base64.urlsafe_b64encode(hasher.digest())

_fernet = None
if Fernet:
    try:
        _fernet = Fernet(get_fernet_key(settings.secret_key))
    except Exception as e:
        print(f"[Paywall Service] Failed to initialize Fernet: {e}")
        _fernet = None

def encrypt_cookie(cookie_str: str) -> str:
    if not cookie_str:
        return ""
    if _fernet:
        return _fernet.encrypt(cookie_str.encode('utf-8')).decode('utf-8')
    else:
        # Fallback if cryptography fails for some reason
        return base64.b64encode(cookie_str.encode('utf-8')).decode('utf-8')

def decrypt_cookie(encrypted_str: str) -> str:
    if not encrypted_str:
        return ""
    if _fernet:
        try:
            return _fernet.decrypt(encrypted_str.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""
    else:
        try:
            return base64.b64decode(encrypted_str.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""

def save_media_cookie(domain: str, media_name: str, cookie_str: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    encrypted = encrypt_cookie(cookie_str)
    
    try:
        cursor.execute("""
            INSERT INTO media_credentials (domain, media_name, encrypted_cookie)
            VALUES (?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                media_name=excluded.media_name,
                encrypted_cookie=excluded.encrypted_cookie
        """, (domain, media_name, encrypted))
        conn.commit()
    except Exception as e:
        print(f"[Paywall Service] Error saving media cookie: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_media_cookie(domain: str) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT encrypted_cookie FROM media_credentials WHERE domain = ?", (domain,))
        row = cursor.fetchone()
        if row:
            return decrypt_cookie(row["encrypted_cookie"])
        return None
    except Exception as e:
        print(f"[Paywall Service] Error getting media cookie: {e}")
        return None
    finally:
        conn.close()

def delete_media_cookie(domain: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM media_credentials WHERE domain = ?", (domain,))
        conn.commit()
    except Exception as e:
        print(f"[Paywall Service] Error deleting media cookie: {e}")
        conn.rollback()
    finally:
        conn.close()

def list_media_credentials() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT domain, media_name, created_at FROM media_credentials")
        rows = cursor.fetchall()
        return [{"domain": row["domain"], "media_name": row["media_name"], "active": True} for row in rows]
    except Exception as e:
        print(f"[Paywall Service] Error listing media credentials: {e}")
        return []
    finally:
        conn.close()

def detect_paywall(html_content: str, text_content: str) -> bool:
    """
    Detects if an article is behind a paywall based on HTML structure and text length.
    """
    if not html_content and not text_content:
        return False
        
    html_lower = (html_content or "").lower()
    text_lower = (text_content or "").lower()
    
    # 1. Check JSON-LD
    if '"isaccessibleforfree": false' in html_lower or '"isaccessibleforfree": "false"' in html_lower:
        return True
        
    # 2. Check CSS Classes/IDs
    paywall_classes = [
        "class=\"paywall\"", "class='paywall'", 
        "class=\"premium-article\"", "class='premium-article'",
        "id=\"reserve-abonne\"", "id='reserve-abonne'",
        "class=\"article-restricted\"", "class='article-restricted'",
        "class=\"lock-icon\"", "class='lock-icon'",
        "id=\"paywall\"", "id='paywall'"
    ]
    for cls in paywall_classes:
        if cls in html_lower:
            return True
            
    # 3. Key Phrases
    key_phrases = [
        "article réservé aux abonnés",
        "abonnez-vous pour lire la suite",
        "subscribe to read full article",
        "cet article est réservé aux abonnés"
    ]
    for phrase in key_phrases:
        if phrase in text_lower or phrase in html_lower:
            return True
            
    # 4. Extracted content too short
    if text_content:
        words = text_content.split()
        if len(words) > 0 and len(words) < 180:
            return True
            
    return False
