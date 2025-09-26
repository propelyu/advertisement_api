from fastapi import Form, File, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id, genai_client
from typing import Annotated, Optional
import cloudinary
import cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# Create users router
adverts_router = APIRouter()


# GET All Adverts
@adverts_router.get("/adverts", tags=["Adverts"])
def get_all_adverts(
    search: str | None = None,
    category: str | None = None,
    price: float | None = None,
    limit: int = 10,
    skip: int = 0,
):

    # Building query
    query_filter = {}

    if search:
        query_filter["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]

    if category:
        query_filter["category"] = {"$regex": f"^{category}$", "$options": "i"}

    if price is not None:
        query_filter["price"] = price

    # Get all adverts from the database, using filters for title and description
    adverts = adverts_collection.find(
        filter=query_filter, limit=limit, skip=skip
    ).to_list()

    # Return a list of adverts
    return {"data": list(map(replace_mongo_id, adverts))}


# POST Advert
# This endpoint creates a new advert
@adverts_router.post(
    "/adverts", dependencies=[Depends(has_roles(["vendor", "admin"]))], tags=["Adverts"]
)
def post_advert(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    location: Annotated[str, Form()],
    user_id: Annotated[dict, Depends(is_authenticated)],
    image: Annotated[bytes, File()]=None,
):

    if not image:
        response = genai_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        image = response.generated_images[0].image.image_bytes

    # Ensure an event with a title and user_id combined does not exist
    advert_count = adverts_collection.count_documents(
        filter={"$and": [{"title": title}, {"owner": user_id["id"]}]}
    )
    if advert_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event with {title} and {user_id} already exist!",
        )

    # Upload the advert image to Cloudinary to get a URL
    upload_result = cloudinary.uploader.upload(image)

    # Inserting the new advert to database
    adverts_collection.insert_one(
        {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "location": location,
            "image_url": upload_result["secure_url"],
            "owner": user_id["id"],
        }
    )

    # Return a success message
    return {"message": "Advert added successfully"}


# Get all Adverts vendor owns
@adverts_router.get("/adverts/vendor", tags=["Vendor Adverts"])
def get_vendor_adverts(user_id: Annotated[dict, Depends(is_authenticated)]):
    if user_id["role"] != "vendor":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only vendors can access their adverts"
        )

    adverts = adverts_collection.find({"owner": user_id["id"]}).to_list()

    return {"data": list(map(replace_mongo_id, adverts))}


# GET Advert Details
@adverts_router.get("/adverts/{advert_id}", tags=["Adverts"])
def get_advert_by_id(advert_id: str):
    # Checking if the provided ID is a valid MongoDB ObjectId
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid advert ID received!"
        )

    # Finding the advert in the database
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})

    # If no advert is found, raise a 404 error
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")

    # Return the advert details after converting the MongoDB ID
    return {"data": replace_mongo_id(advert)}


@adverts_router.get("/adverts/{advert_id}/similar", tags=["Adverts"])
def get_similar_adverts(advert_id, limit=10, skip=0):
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get advert from database by id
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    # Get similar events from database
    adverts = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": advert["title"], "$options": "i"}},
                {"description": {"$regex": advert["description"], "$options": "i"}},
                {"venue": {"$regex": advert["description"], "$options": "i"}},
            ]
        },
        limit=int(limit),
        skip=int(skip),
    ).to_list()
    return {"data": list(map(replace_mongo_id, adverts))}


### Adverts Update Endpoints
# ---------- UPDATE / REPLACE ADVERT ----------
@adverts_router.put(
    "/adverts/{advert_id}",
    tags=["Adverts Update"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def update_advert(
    advert_id: str,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    location: Annotated[str, Form()],
    user_id: Annotated[dict, Depends(is_authenticated)],
    image: Annotated[Optional[bytes], File()] = None,
):
    # ensure valid mongo id first
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid advert ID received!"
        )

    # only vendors can update
    if user_id["role"] != "vendor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only vendors can update adverts")

    # confirm advert exists
    existing_advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not existing_advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Advert not found")

    # ensure ownership
    if existing_advert.get("owner") != user_id["id"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You can update only your own advert"
        )

    # generate or upload image
    if not image:
        response = genai_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        image = response.generated_images[0].image.image_bytes

    upload_result = cloudinary.uploader.upload(image)
    update_data = {
        "title": title,
        "description": description,
        "price": price,
        "category": category,
        "location": location,
        "owner": user_id["id"],
        "image_url": upload_result["secure_url"],
    }

    replace_result = adverts_collection.replace_one(
        {"_id": ObjectId(advert_id)}, update_data
    )
    if not replace_result.modified_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No advert found to update")

    return {"message": "Advert updated successfully"}


# ---------- DELETE ADVERT ----------
@adverts_router.delete(
    "/adverts/{advert_id}",
    tags=["Adverts Update"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def delete_advert(
    advert_id: str,
    user_id: Annotated[dict, Depends(is_authenticated)],
):
    # validate id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid advert ID received!"
        )

    # only vendors can delete
    if user_id["role"] != "vendor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only vendors can delete adverts")

    # ensure advert belongs to user
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Advert not found")
    if advert.get("owner") != user_id["id"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You can delete only your own advert"
        )

    delete_result = adverts_collection.delete_one(
        {"_id": ObjectId(advert_id)}
    )
    if not delete_result.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No advert found to delete")

    return {"message": "Advert deleted successfully!", "user_id": user_id["id"]}