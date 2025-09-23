from fastapi import FastAPI
from pydantic import BaseModel
import cloudinary
import os
from dotenv import load_dotenv
from routes.adverts import adverts_router
from routes.users import users_router

load_dotenv()

# Connecting to Cloudinary for image uploads
cloudinary.config(
    cloud_name= os.getenv("CLOUD_NAME"),
    api_key= os.getenv("API_KEY"),
    api_secret= os.getenv("API_SECRET"),
)

# Metadata for API documentation (tags)
tags_metadata = [
    {
        "name": "Home",
        "description": "Welcome to the Advert Manager",
    },
    {
        "name": "Adverts",
        "description": "Advertisement list and management",
    },
    {
        "name": "Vendor Adverts",
        "description": "Managing adverts for vendors",
    },
    {
        "name": "Adverts Update",
        "description": "Updating and deleting adverts"
    },
    {
        "name": "Users",
        "description": "Registering users and user authentication",
    },
]

# Pydantic model 
class AdvertModel(BaseModel):
    title: str
    description: str
    price: float
    category: str

# Creating the FastAPI application 
app = FastAPI(
    title="🏠Propelu Real Estate Advertisement API ",
    description="We give you nothing but the best and yet very affordable",
    openapi_tags=tags_metadata)

# Endpoints
# Home Endpoint

@app.get("/", status_code=200, tags=["Home"])
def get_home():
    return {"message": "Hallo, willkommen bei der Adver API!"}

# Include routers
app.include_router(adverts_router)
app.include_router(users_router)