import pymongo
import os
from munch import Munch
from app.constants import *

print()
MONGO_USERNAME = os.getenv('MONGO_USERNAME')    # ; print(MONGO_USERNAME)
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')    # ; print(MONGO_PASSWORD)
MONGO_SERVER = os.getenv('MONGO_SERVER')        # ; print(MONGO_SERVER)
MONGO_PORT = os.getenv('MONGO_PORT')            # ; print(MONGO_PORT)
MONGO_DB = os.getenv('MONGO_DB')                # ; print(MONGO_DB)
CHAT_COLLECTION = 'chat_collection'

# https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls
# URL format: dialect+driver://username:password@host:port/database
MONGO_DATABASE_URL = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_SERVER}:{MONGO_PORT}/"
print(MONGO_DATABASE_URL)

def get_db():
    client = pymongo.MongoClient(MONGO_DATABASE_URL)
    db = client[MONGO_DB]
    try:
        yield db
    finally:
        client.close()

def add_chat_collection(update: Munch, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    # delete the chat_id document if it exists
    if len(list(chat_collection.find({'chat_id': update.message.chat.id}, {}))) != 0:
        chat_collection.delete_many({'chat_id': update.message.chat.id})
    
    # create a new chat_id document with default config and empty list for deleting messages 
    data = {
        "chat_id": update.message.chat.id,
        "messages": [],
        "config": {}
    }
    x = chat_collection.insert_one(data)
    assert x.acknowledged == True

def update_chat_configs(update: Munch, db: pymongo.database.Database, chat_config: dict):
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": update.message.chat.id }
    newvalues = {"$set" : {"config": chat_config}}
    chat_collection.update_one(query, newvalues)
