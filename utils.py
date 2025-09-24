from google import genai
from dotenv import load_dotenv

load_dotenv()

genai_client = genai.Client()

def replace_mongo_id(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc