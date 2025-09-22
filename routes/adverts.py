from fastapi import Form, File, UploadFile, HTTPException, status, APIRouter, Depends, Query
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader
from typing import Optional
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles



# Create users router
adverts_router = APIRouter()


# GET All Adverts
@adverts_router.get("/adverts", tags=["Adverts"])
def get_all_adverts(
    title: Optional[str] = Query("", description="Search by title"), 
    description: Optional[str] = Query("", description="Search by description" ), 
    location: Optional[str] = Query("", description="Search by location"),
    category: Optional[str] = Query(None, description="Filter by category(optional)"),
    price: Optional[float] = Query(None, description="Filter by price (optional)"),
    limit: int = Query(10, ge=1, le=100), 
    skip: int = Query(0, ge=0),
    ):

    # Building query
    query = {
        "$or": [
            {"title": {"$regex": title, "$options": "i"}},
            {"description": {"$regex": description, "$options": "i"}},
        ]
    }

    # Optional location match (if provided)
    if location: 
        query["$or"].append({"location": {"$regex": location, "$options": "i"}})
    
    if category: 
        query["category"] = category.lower().strip()

    if price is not None:
        query["price"] = price


    # Get all adverts from the database, using filters for title and description
    adverts = adverts_collection.find(
        filter=query,
        limit=limit,
        skip=skip
    ).to_list()
    
    # Return a list of adverts 
    return {"data": list(map(replace_mongo_id, adverts))}

# POST Advert
# This endpoint creates a new advert
@adverts_router.post("/adverts", dependencies=[Depends(has_roles(["vendor", "admin"]))], tags=["Adverts"])
def post_advert(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    location: Annotated[str, Form()],
    image: Annotated[UploadFile, File()],
    user_id: Annotated[dict, Depends(is_authenticated)]
):
    
    
    # Ensure an event with a title and user_id combined does not exist
    advert_count = adverts_collection.count_documents(filter={
        "$and": [
            {"title": title},
            {"owner": user_id["id"]}
        ]
    })
    if advert_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event with {title} and {user_id} already exist!",
        )


    # Upload the advert image to Cloudinary to get a URL
    upload_result = cloudinary.uploader.upload(image.file)
    
    # Inserting the new advert to database
    adverts_collection.insert_one({
        "title": title,
        "description": description,
        "price": price,
        "category": category,
        "location": location,
        "image_url": upload_result["secure_url"],
        "owner": user_id["id"]
    })
    
    # Return a success message
    return {"message": "Advert added successfully"}

# GET Advert Details
@adverts_router.get("/adverts/{advert_id}", tags=["Adverts"])
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
@adverts_router.put("/adverts/{advert_id}", tags=["Adverts Update"])
def update_advert(
    advert_id: str,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    location: Annotated[str, Form()],
    user_id: Annotated[dict, Depends(is_authenticated)],
    image: Annotated[Optional[UploadFile], File()] = None
):
    
    if user_id["role"] != "vendor":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid ID")
    
    # Check for a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!")

    # Check if the advert exists before updating
    existing_advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not existing_advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")
    
    # Ensuring user owns the advert
    if existing_advert.get("owner") !=user_id["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can update only your own advert")

    # Preparing the update data
    update_data = {
        "title": title,
        "description": description,
        "price": price,
        "category": category,
        "location": location,
        "owner": user_id["id"],
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
@adverts_router.delete("/adverts/{advert_id}", tags=["Adverts Update"])
def delete_advert(advert_id: str, user_id: Annotated[str, Depends(is_authenticated)]):
    
    # ensuring only vendors can delete
    if user_id["role"] != "vendor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only vendors can delete adverts")
    
    # Check for a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!")
    
    # Checking if the advert exists and belongs to the user
    advert = adverts_collection.find_one(filter={"_id": ObjectId(advert_id)})
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")
    
    if advert.get("owner") !=user_id["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can delete only your own advert")
    
    # Delete the advert from the database
    delete_result = adverts_collection.delete_one(filter={"_id": ObjectId(advert_id)})
    
    # If no advert was deleted, raise a 404 error
    if not delete_result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No advert found to delete")
        
    # Return a success message
    return {"message": "Advert deleted successfully!"}