from fastapi import APIRouter, Form, Depends
from dependencies.authn import is_authenticated
from utils import genai_client
from typing import Annotated

# Create genai router
genai_router = APIRouter(tags=["GenAI"])

# Define Router
@genai_router.post("/genai/generate-text", dependencies=[Depends(is_authenticated)])
def generate_text(prompt: Annotated[str, Form()]):
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return {"content": response.text}