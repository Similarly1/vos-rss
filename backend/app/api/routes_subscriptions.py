from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List

from app.services.paywall import list_media_credentials, save_media_cookie, delete_media_cookie, auto_subscribe_to_media_feeds

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

class CredentialItem(BaseModel):
    domain: str
    media_name: str
    cookie: str

@router.get("/credentials")
def get_credentials():
    try:
        credentials = list_media_credentials()
        return credentials
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/credentials")
def add_credential(item: CredentialItem, background_tasks: BackgroundTasks):
    try:
        save_media_cookie(item.domain, item.media_name, item.cookie)
        # Auto-subscribe to catalog feeds for this domain
        auto_subscribed = auto_subscribe_to_media_feeds(item.domain, item.media_name)

        # Trigger background RSS refresh for newly subscribed feeds
        if auto_subscribed:
            def _refresh():
                try:
                    from app.services.rss import fetch_all_feeds
                    fetch_all_feeds()
                except Exception as e:
                    print(f"[AutoSubscribe Refresh] {e}")
            background_tasks.add_task(_refresh)

        return {
            "status": "success",
            "domain": item.domain,
            "auto_subscribed": auto_subscribed,
            "message": f"Cookie enregistré. {len(auto_subscribed)} flux ajouté(s) automatiquement." if auto_subscribed else "Cookie enregistré."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/credentials/{domain}")
def remove_credential(domain: str):
    try:
        delete_media_cookie(domain)
        return {"status": "success", "domain": domain}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

