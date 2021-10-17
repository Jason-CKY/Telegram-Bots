import pymongo
import os
from munch import Munch
from pymongo import client_options
from telegram import poll

print()
MONGO_USERNAME = os.getenv('MONGO_USERNAME')    # ; print(MONGO_USERNAME)
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')    # ; print(MONGO_PASSWORD)
MONGO_SERVER = os.getenv('MONGO_SERVER')        # ; print(MONGO_SERVER)
MONGO_PORT = os.getenv('MONGO_PORT')            # ; print(MONGO_PORT)
MONGO_DB = os.getenv('MONGO_DB')                # ; print(MONGO_DB)
CHAT_COLLECTION = 'reminder'

# https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls
# URL format: dialect+driver://username:password@host:port/database
MONGO_DATABASE_URL = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_SERVER}:{MONGO_PORT}/"
print(MONGO_DATABASE_URL)

def get_client():
    return pymongo.MongoClient(MONGO_DATABASE_URL)
    

def get_db():
    client = pymongo.MongoClient(MONGO_DATABASE_URL)
    db = client[MONGO_DB]
    try:
        yield db
    finally:
        client.close()
