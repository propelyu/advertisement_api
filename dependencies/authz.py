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
            "post_event", 
            "get_events", 
            "get_event", 
            "put_event", 
            "delete_event"]
    },
    {
         "role": "guest",
        "permissions": [
            "get_events", 
            "get_event"]
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
    def checK_permission(user: Annotated[any, Depends(authenticated_user)]):
        role = user.get("role")
        for entry in permissions:
            if entry["role"] == role:
                perms = entry.get("permissions", [])
                if "*" in perms or permission in perms:
                    return user
                break
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return checK_permission
            
