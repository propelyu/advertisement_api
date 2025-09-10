from fastapi import FastAPI, Form, File, UploadFile, HTTPException, status
from db import adverts_collection
from pydantic import BaseModel
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Connecting to Cloudinary for image uploads
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
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
        "name": "Adverts Update",
        "description": "Updating and deleting adverts"
    },
]

# Pydantic model 
class AdvertModel(BaseModel):
    title: str
    description: str
    price: float
    category: str

# Creating the FastAPI application 
app = FastAPI(openapi_tags=tags_metadata)

# Endpoints
# Home Endpoint

@app.get("/", status_code=200, tags=["Home"])
def get_home():
    return {"message": "Hallo! Gern Geschehen, to the Advert Manager API"}

# Advert Endpoints
# GET All Adverts

@app.get("/adverts", tags=["Adverts"])
def get_all_adverts(title: Optional[str] = "", description: Optional[str] = "", limit: int = 10, skip: int = 0):
    
    # Get all adverts from the database, using filters for title and description
    adverts = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": title, "$options": "i"}},
                {"description": {"$regex": description, "$options": "i"}},
            ]
        },
        limit=limit,
        skip=skip
    ).to_list()
    
    # Return a list of adverts 
    return {"data": list(map(replace_mongo_id, adverts))}

# POST Advert
# This endpoint creates a new advert
@app.post("/adverts", tags=["Adverts"])
def post_advert(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    image: Annotated[UploadFile, File()]
):
    # Upload the advert image to Cloudinary to get a URL
    upload_result = cloudinary.uploader.upload(image.file)
    
    # Inserting the new advert to database
    adverts_collection.insert_one({
        "title": title,
        "description": description,
        "price": price,
        "category": category,
        "image_url": upload_result["secure_url"]
    })
    
    # Return a success message
    return {"message": "Advert added successfully"}

# GET Advert Details
@app.get("/adverts/{advert_id}", tags=["Adverts"])
def get_advert_by_id(advert_id: str):
    # Checking if the provided ID is a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!")
    
    # Finding the advert in the database
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    
    # If no advert is found, raise a 404 error
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")
        
    # Return the advert details after converting the MongoDB ID
    return {"data": replace_mongo_id(advert)}

### Adverts Update Endpoints

# PUT Advert
# This endpoint updates an existing advert by its ID
@app.put("/adverts/{advert_id}", tags=["Adverts Update"])
def update_advert(
    advert_id: str,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    image: Annotated[Optional[UploadFile], File()] = None
):
    # Check for a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!")

    # Check if the advert exists before updating
    existing_advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not existing_advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")

    # Prepare the update data
    update_data = {
        "title": title,
        "description": description,
        "price": price,
        "category": category,
    }

    # uploading a new image
    if image:
        upload_result = cloudinary.uploader.upload(image.file)
        update_data["image_url"] = upload_result["secure_url"]

    # Replace the advert document in the database
    adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id)},
        replacement=update_data,
    )
    
    # Return a success message
    return {"message": "Advert updated successfully"}

# DELETE Advert
@app.delete("/adverts/{advert_id}", tags=["Adverts Update"])
def delete_advert(advert_id: str):
    # Check for a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!")
    
    # Delete the advert from the database
    delete_result = adverts_collection.delete_one(filter={"_id": ObjectId(advert_id)})
    
    # If no advert was deleted, raise a 404 error
    if not delete_result.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No advert found to delete")
        
    # Return a success message
    return {"message": "Advert deleted successfully!"}