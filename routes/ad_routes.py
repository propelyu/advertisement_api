from fastapi import APIRouter, HTTPException, Depends
from fastapi import FastAPI
from models.ad_model import Ad
from controllers import ad_controller

router = APIRouter()

#  Dependency to get database from app 
def get_db(app: FastAPI):
    return app.database

#  Create a new ad 
@router.post("/", response_model=dict)
async def create_ad(ad: Ad, db=Depends(get_db)):
    ad_id = await ad_controller.create_ad(db, ad.dict())
    return {"id": ad_id, "message": "Ad created successfully"}

#  Get all ads
@router.get("/", response_model=list)
async def get_all_ads(db=Depends(get_db)):
    ads = await ad_controller.get_all_ads(db)
    return ads

#  Get a single ad by ID
@router.get("/{ad_id}", response_model=dict)
async def get_ad(ad_id: str, db=Depends(get_db)):
    ad = await ad_controller.get_ad(db, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    return ad

# Update an ad
@router.put("/{ad_id}", response_model=dict)
async def update_ad(ad_id: str, ad: Ad, db=Depends(get_db)):
    updated = await ad_controller.update_ad(db, ad_id, ad.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "Ad updated successfully"}

# Delete an ad
@router.delete("/{ad_id}", response_model=dict)
async def delete_ad(ad_id: str, db=Depends(get_db)):
    deleted = await ad_controller.delete_ad(db, ad_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"message": "Ad deleted successfully"}
