from fastapi import FastAPI

#  Defining tags
tags_metadata = [
     {
        "name": "Home",
        "description": "Welcome to the Propelyu Advertisement Api",
    },
]

# Adding openapi_tags to fastapi app 
app = FastAPI(openapi_tags=tags_metadata)

@app.get("/", tags=["Home"])
def get_home():
    return {"message": "Welcome to our ecommerce site"}