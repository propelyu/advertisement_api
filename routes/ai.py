from fastapi import APIRouter, HTTPException, status
from ai_features import (
    suggest_price, 
    suggest_similar_houses, 
    PriceSuggestionRequest,
    train_price_suggestion_model
)

ai_router = APIRouter(prefix="/ai", tags=["AI Features"])

@ai_router.post("/suggest-price")
def get_price_suggestion(request: PriceSuggestionRequest):
    """
    Suggests a price for a property based on its category and description
    using a machine learning model.
    """
    suggestion = suggest_price(request)
    return suggestion

@ai_router.get("/similar-houses/{advert_id}")
def get_similar_houses(advert_id: str):
    """
    Suggests houses similar to the one with the given advert_id.
    Similarity is based on the same category and a similar price range.
    """
    similar = suggest_similar_houses(advert_id)
    if similar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advert not found")
    if "error" in similar:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=similar["error"])
    return {"similar_adverts": similar}

@ai_router.post("/retrain-model", status_code=status.HTTP_202_ACCEPTED)
def retrain_model():
    """
    Triggers a retraining of the price suggestion model.
    """
    train_price_suggestion_model()
    return {"message": "Model retraining initiated."}