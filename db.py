from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB Atlas Cluster
mongo_client = MongoClient(os.getenv("MONGO_URI"))

# Access the database
ad_manager_db = mongo_client["advertisement_api"]

# Pick a new collection to operate on
adverts_collection = ad_manager_db["adverts"]

