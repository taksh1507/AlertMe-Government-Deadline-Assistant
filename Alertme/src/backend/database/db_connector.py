"""Database creation is owned by the application factory."""

import os
from pymongo import MongoClient


def create_client():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is required")
    return MongoClient(
        uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000, socketTimeoutMS=5000
    )
