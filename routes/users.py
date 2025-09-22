from fastapi import APIRouter, Form, HTTPException, status
from typing import Annotated
from pydantic import EmailStr
from db import users_collection
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
import re
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VENDOR = "vendor"
    GUEST = "guest"
    
# create users router
users_router = APIRouter()

# Helper function to validate password strength
def validate_password_strength(password: str) -> bool:
    # Require: 
    # At least 8 characters
    # one uppercase letter
    # one lowercase letter
    # one digit
    # one special character

    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$'
    return re.match(pattern, password) is not None


#Define endpoints
@users_router.post("/users/register", tags=["Users"])
def register_user(
    username: Annotated[str, Form()],
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
    confirm_password: Annotated[str, Form(min_length=8)],
    role: Annotated[UserRole, Form()] = UserRole.GUEST,
    ):

    # Make sure passwords match
    if password != confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwods do not match.")


    # Preventing people from registering directly as admin
    if role == UserRole.ADMIN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot register as admin. Admin role is assigned manually, Please select a different role",
        )

    # Ensure user does not exist
    user_count = users_collection.count_documents(filter={"email": email})
    if user_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exist!")
    
    # Validate password strength
    if not validate_password_strength(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Password must be at least 8 characters long and include "
                "one uppercase letter, one lowercase letter, one number, and one special character."
                
            )
        )


    # Hash user password
    hashed_password = bcrypt.hashpw(bytes(password.encode("utf-8")), bcrypt.gensalt())
    
    # Save user into database
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password.decode("utf-8"),
        "role": role.value,
    })

    #Return response
    return {"message": "User registered successfully!"}

@users_router.post("/users/login", tags=["Users"])
def login_user(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
):
    # Checking if the user exists
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist!"
        )

    # Verifying password
    hashed_password_in_db = user["password"]
    correct_password = bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password_in_db.encode("utf-8")
    )

    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Generate for them an access token
    encoded_iwt = jwt.encode({
        "id": str(user["_id"]),
        "role": user["role"],
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1)
    }, os.getenv("JWT_SECRET_KEY"), "HS256")

    return {
        "message": "User logged in successfully!",
        "access_token": encoded_iwt
    }