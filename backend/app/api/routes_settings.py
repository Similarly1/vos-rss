from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from pathlib import Path
from app.services.podcast import set_app_setting, get_app_setting
import json

router = APIRouter(prefix="/api/settings", tags=["Settings"])

CATEGORIES = ["Général", "International", "Économie", "Technologie", "Science", "Culture", "Sports", "Santé", "Environnement"]
STATIC_DIR = Path("static/categories")

@router.get("/categories")
def get_category_images():
    # Load custom mapping from DB
    custom_mapping_str = get_app_setting("category_images", "{}")
    try:
        custom_mapping = json.loads(custom_mapping_str)
    except:
        custom_mapping = {}

    res = []
    for cat in CATEGORIES:
        custom_url = custom_mapping.get(cat)
        # Default placeholder if no custom image
        # Using a nice generic placeholder based on the category name
        default_url = f"https://placehold.co/600x400/eeeeee/333333?text={cat}"
        res.append({
            "category": cat,
            "image_url": custom_url or default_url,
            "is_custom": bool(custom_url)
        })
    return {"status": "success", "data": res}

@router.post("/categories/{category}")
async def upload_category_image(category: str, file: UploadFile = File(...)):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
        
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    
    file_extension = file.filename.split(".")[-1]
    safe_cat_name = "".join(c if c.isalnum() else "_" for c in category.lower())
    filename = f"{safe_cat_name}.{file_extension}"
    file_path = STATIC_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    custom_url = f"/static/categories/{filename}"
    
    custom_mapping_str = get_app_setting("category_images", "{}")
    try:
        custom_mapping = json.loads(custom_mapping_str)
    except:
        custom_mapping = {}
        
    custom_mapping[category] = custom_url
    set_app_setting("category_images", json.dumps(custom_mapping))
    
    return {"status": "success", "image_url": custom_url}

@router.delete("/categories/{category}")
def reset_category_image(category: str):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
        
    custom_mapping_str = get_app_setting("category_images", "{}")
    try:
        custom_mapping = json.loads(custom_mapping_str)
    except:
        custom_mapping = {}
        
    if category in custom_mapping:
        del custom_mapping[category]
        set_app_setting("category_images", json.dumps(custom_mapping))
        
    return {"status": "success"}
