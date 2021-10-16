import pymongo
import os
from munch import Munch
from telegram import poll
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

def get_client():
    return pymongo.MongoClient(MONGO_DATABASE_URL)

def get_db():
    client = pymongo.MongoClient(MONGO_DATABASE_URL)
    db = client[MONGO_DB]
    try:
        yield db
    finally:
        client.close()

def config_exists(chat_id: int, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    return list(chat_collection.find({ "chat_id": chat_id }, {"_id": 0, "config": 1})) == []

def query_for_chat_id(chat_id: int, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({ "chat_id": chat_id }))
    if len(query) == 0:
        raise AssertionError("This group chat ID does not exist in the database!")
    
    return query

def query_for_poll_id(poll_id: str, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({ "messages.poll_id": poll_id }))
    if len(query) == 0:
        raise AssertionError("No such poll exists in this chat")

    return query

def delete_chat_collection(chat_id: int, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    chat_collection.delete_many({'chat_id': chat_id})

def remove_message_from_db(chat_id: int, offending_message_id: int, db: pymongo.database.Database):
    query = query_for_chat_id(chat_id, db)[0]['messages']
    new_messages = [q for q in query if q['offending_message_id'] != offending_message_id]
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": chat_id }
    newvalues = {"$set" : {"messages": new_messages}}
    chat_collection.update_one(query, newvalues)
    
def add_chat_collection(update: Munch, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    # delete the chat_id document if it exists
    if len(list(chat_collection.find({'chat_id': update.message.chat.id}))) != 0:
        chat_collection.delete_many({'chat_id': update.message.chat.id})
    
    # create a new chat_id document with default config and empty list for deleting messages 
    data = {
        "chat_id": update.message.chat.id,
        "messages": [],
        "config": {}
    }
    x = chat_collection.insert_one(data)

def set_chat_configs(update: Munch, db: pymongo.database.Database, chat_config: dict):
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": update.message.chat.id }
    newvalues = {"$set" : {"config": chat_config}}
    chat_collection.update_one(query, newvalues)

def query_for_poll(chat_id: int, offending_message_id: int, db: pymongo.database.Database):
    query = query_for_chat_id(chat_id, db)    
    return [d for d in query[0]['messages'] if d.get('offending_message_id') == offending_message_id]

def is_poll_exists(update: Munch, db: pymongo.database.Database):
    offending_message_id = update.message.reply_to_message.message_id
    chat_id = update.message.chat.id
    poll_data = query_for_poll(chat_id, offending_message_id, db)
    return len(poll_data) > 0

def get_poll_message_id(update: Munch, db: pymongo.database.Database):
    offending_message_id = update.message.reply_to_message.message_id
    chat_id = update.message.chat.id
    poll_data = query_for_poll(chat_id, offending_message_id, db)
    return poll_data[0].get('poll_message_id')

def get_config(chat_id: int, db: pymongo.database.Database):
    '''
    Queries db for the current chat config
    Args:
        update: Munch
        db: pymongo.database.Database
    Returns:
        expiry: int
        threshold: int
    '''
    query = query_for_chat_id(chat_id, db)   
    return query[0]['config']['expiryTime'], query[0]['config']['threshold']

def insert_chat_poll(update: Munch, poll_data: dict, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": update.message.chat.id }
    newvalues = {"$push" : {"messages": poll_data}}
    chat_collection.update_one(query, newvalues)

def get_job_id_from_poll_id(poll_id: str, db: pymongo.database.Database):
    query = query_for_poll_id(poll_id, db)
    return [d['job_id'] for d in query[0]['messages'] if d.get('poll_id') == poll_id][0]

def get_chat_id_from_poll_id(poll_id: str, db: pymongo.database.Database):
    query = query_for_poll_id(poll_id, db)
    return query[0].get('chat_id')

def get_offending_message_id_from_poll_id(poll_id: int, db: pymongo.database.Database):
    query = query_for_poll_id(poll_id, db)
    return [d['offending_message_id'] for d in query[0]['messages'] if d.get('poll_id') == poll_id][0]

def get_poll_message_id_from_poll_id(poll_id: int, db: pymongo.database.Database):
    query = query_for_poll_id(poll_id, db)
    return [d['poll_message_id'] for d in query[0]['messages'] if d.get('poll_id') == poll_id][0]

def update_chat_id(mapping: dict, db: pymongo.database.Database):
    '''
    Update db collection chat id to supergroup chat id
    Args:
        mapping: Dict 
            {
                "chat_id": int
                "supergroup_chat_id": id
            }
        db: pymongo.database.Database
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": mapping['chat_id'] }
    newvalues = {"$set" : {"chat_id": mapping['supergroup_chat_id']}}
    chat_collection.update_one(query, newvalues)
    