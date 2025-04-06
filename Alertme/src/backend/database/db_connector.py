import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB client
client = MongoClient('mongodb://your_mongodb_uri')
db = client['your_database_name']

# Export the db object
__all__ = ['db']