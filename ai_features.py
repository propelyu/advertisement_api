from bson import ObjectId
from pydantic import BaseModel
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.exceptions import NotFittedError
import logging

from db import adverts_collection
from utils import replace_mongo_id


class PriceSuggestionRequest(BaseModel):
    """
    Pydantic model for the data required for a price suggestion.
    """
    category: str
    description: str  # Included for future, more advanced ML models


def suggest_similar_houses(advert_id: str):
    """
    Suggests houses similar to the one with the given advert_id.

    For this placeholder, similarity is based on:
    1. Same category.
    2. Price within a +/- 20% range of the target advert's price.
    """
    if not ObjectId.is_valid(advert_id):
        return {"error": "Invalid advert ID format."}

    target_advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})

    if not target_advert:
        return None  # Or raise HTTPException(404) in the route

    price = target_advert.get("price", 0)
    price_lower_bound = price * 0.8
    price_upper_bound = price * 1.2

    query = {
        "category": target_advert.get("category"),
        "price": {"$gte": price_lower_bound, "$lte": price_upper_bound},
        "_id": {"$ne": ObjectId(advert_id)},
    }

    similar_adverts_cursor = adverts_collection.find(query).limit(5)
    return [replace_mongo_id(doc) for doc in similar_adverts_cursor]


# --- Price Suggestion ML Model ---

# Global model variable and a flag to indicate if it's trained
price_suggestion_model = None
model_is_trained = False

def train_price_suggestion_model():
    """
    Fetches advert data and trains a simple linear regression model.
    The model predicts price based on the TF-IDF of the description.
    """
    global price_suggestion_model, model_is_trained
    
    # Fetch all adverts with description and price
    adverts_data = list(adverts_collection.find(
        {"description": {"$exists": True}, "price": {"$exists": True}},
        {"description": 1, "price": 1}
    ))

    # We need at least two data points to train a linear model
    if len(adverts_data) < 2:
        logging.warning("Not enough data to train price suggestion model. At least 2 adverts are required.")
        price_suggestion_model = None
        model_is_trained = False
        return

    df = pd.DataFrame(adverts_data)

    # Features (X) and labels (y)
    X = df["description"]
    y = df["price"]

    # Simple pipeline: TF-IDF Vectorizer -> Linear Regression
    price_suggestion_model = make_pipeline(TfidfVectorizer(), LinearRegression())
    price_suggestion_model.fit(X, y)
    model_is_trained = True
    logging.info("Price suggestion model trained successfully.")

# Train the model on application startup
train_price_suggestion_model()


def suggest_price(request: PriceSuggestionRequest):
    """
    Suggests a price for a new property using a trained ML model
    based on the property's description.
    """
    if not model_is_trained or price_suggestion_model is None:
        return {"suggested_price": 0, "message": "Price suggestion model is not available due to insufficient data."}
    
    try:
        # Predict price using the description
        predicted_price = price_suggestion_model.predict([request.description])[0]
        # Ensure price is not negative and round it
        suggested_price = max(0, round(predicted_price, 2))
        return {"suggested_price": suggested_price}
    except NotFittedError:
         return {"suggested_price": 0, "message": "Model is not fitted yet."}