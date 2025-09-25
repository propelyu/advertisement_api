from dependencies.authn import authenticated_user
from fastapi import Depends, HTTPException, status
from typing import Annotated


permissions = [
    {
        "role": "admin",
        "permissions": ["*"]
    },
    {
         "role": "vendor",
        "permissions": [
            "post_advert",
            "get_all_adverts", 
            "get_vendor_adverts",
            "get_advert_by_id",
            "get_similar_adverts",
            "update_advert", 
            "delete_advert"]
    },
    {
         "role": "guest",
        "permissions": [
            "get_all_adverts", 
            "get_advert_by_id",
            "get_similar_adverts"]
    },
]
    
       


def has_roles(roles):
    def check_roles(user: Annotated[any, Depends(authenticated_user)]):
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied!",
            )
        return user
    
    return check_roles

def has_permission(permission):
    def check_permission(user: Annotated[any, Depends(authenticated_user)]):
        role = user.get("role")
        for entry in permissions:
            if entry["role"] == role:
                perms = entry.get("permissions", [])
                if "*" in perms or permission in perms:
                    return user
                break
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return check_permission
            
