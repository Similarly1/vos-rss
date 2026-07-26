from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List

from app.services.paywall import list_media_credentials, save_media_cookie, delete_media_cookie

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
def add_credential(item: CredentialItem):
    try:
        save_media_cookie(item.domain, item.media_name, item.cookie)
        return {"status": "success", "domain": item.domain}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/credentials/{domain}")
def remove_credential(domain: str):
    try:
        delete_media_cookie(domain)
        return {"status": "success", "domain": domain}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
