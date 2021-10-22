import pymongo
import os
from munch import Munch
from typing import List
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
    '''
    Yield a database connection. Used as a fastapi Dependency for the /webhook endpoint.
    Close the database client after yielding the database connection.
    '''
    client = pymongo.MongoClient(MONGO_DATABASE_URL)
    db = client[MONGO_DB]
    try:
        yield db
    finally:
        client.close()

def config_exists(chat_id: int, db: pymongo.database.Database) -> bool:
    '''
    Returns True if config exists on the chat group in the mongo database
    '''
    chat_collection = db[CHAT_COLLECTION]
    return list(chat_collection.find({ "chat_id": chat_id }, {"_id": 0, "config": 1})) == []

def query_for_chat_id(chat_id: int, db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the chat query with messages that contains the given chat id. By right this should only
    return a list of 1 entry as chat ids are unique to each chat, but return the entire query regardless
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({ "chat_id": chat_id }))
    if len(query) == 0:
        raise AssertionError("This group chat ID does not exist in the database!")
    
    return query

def query_for_poll_id(poll_id: str, db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the chat query with messages that contains the given poll id. By right this should only
    return a list of 1 entry as poll ids are unique to each poll, but return the entire query regardless
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({ "messages.poll_id": poll_id }))
    if len(query) == 0:
        raise AssertionError("No such poll exists in this chat")

    return query

def query_for_job_id(job_id: str, db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the chat query with messages that contains the given job id. By right this should only
    return a list of 1 entry as job ids are unique to each job, but return the entire query regardless
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({ "messages.job_id": job_id }))
    if len(query) == 0:
        raise AssertionError("No such job exists in this chat")

    return query

def delete_chat_collection(chat_id: int, db: pymongo.database.Database) -> List[dict]:
    '''
    Deletes the entire entry that matches the chat id. This helps to clean up the database once the bot is removed from the group
    '''
    chat_collection = db[CHAT_COLLECTION]
    chat_collection.delete_many({'chat_id': chat_id})

def remove_message_from_db(chat_id: int, offending_message_id: int, db: pymongo.database.Database) -> None:
    '''
    Delete the message entry in the chat id inside mongodb
    '''
    query = query_for_chat_id(chat_id, db)[0]['messages']
    new_messages = [q for q in query if q['offending_message_id'] != offending_message_id]
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": chat_id }
    newvalues = {"$set" : {"messages": new_messages}}
    chat_collection.update_one(query, newvalues)
    
def add_chat_collection(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Add a new db entry with the chat id within the update json object. It is initialized
    with empty config. Call the set_chat_configs function to fill in the config with dynamic values.
    '''
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

def set_chat_configs(update: Munch, db: pymongo.database.Database, chat_config: dict) -> None:
    '''
    Set the config key with given chat config in the database for the current chat group id
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": update.message.chat.id }
    newvalues = {"$set" : {"config": chat_config}}
    chat_collection.update_one(query, newvalues)

def query_for_poll(chat_id: int, offending_message_id: int, db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the messages key of the query with messages that contains the offending message id. By right this should only
    return a list of 1 entry as message ids are unique to each message, but return the entire query regardless.
    Offending message id refers to the message id of the message to delete
    '''
    query = query_for_chat_id(chat_id, db)    
    return [d for d in query[0]['messages'] if d.get('offending_message_id') == offending_message_id]

def is_poll_exists(update: Munch, db: pymongo.database.Database) -> bool:
    '''
    Returns True if poll exists. Takes in the update from telegram webhook and extracts the chat id and the message that it is replying to id 
    to query database for relevant entry.
    '''
    offending_message_id = update.message.reply_to_message.message_id
    chat_id = update.message.chat.id
    poll_data = query_for_poll(chat_id, offending_message_id, db)
    return len(poll_data) > 0

def get_poll_message_id(update: Munch, db: pymongo.database.Database) -> int:
    '''
    Takes in the update from telegram webhook and extracts the chat id and the message that it is replying to id 
    to query database for relevant entry. Returns the message id of the poll in question.
    '''
    offending_message_id = update.message.reply_to_message.message_id
    chat_id = update.message.chat.id
    poll_data = query_for_poll(chat_id, offending_message_id, db)
    return poll_data[0].get('poll_message_id')

def get_config(chat_id: int, db: pymongo.database.Database) -> dict:
    '''
    Queries db for the current chat config
    Args:
        update: Munch
        db: pymongo.database.Database
    Returns:
        {
            "expiry": int
            "threshold": int
        }
    '''
    query = query_for_chat_id(chat_id, db)   
    return query[0]['config']['expiryTime'], query[0]['config']['threshold']

def insert_chat_poll(update: Munch, poll_data: dict, db: pymongo.database.Database) -> None:
    '''
    append the messages key with a new entry and push it to the database
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = { "chat_id": update.message.chat.id }
    newvalues = {"$push" : {"messages": poll_data}}
    chat_collection.update_one(query, newvalues)

def get_poll_id_from_job_id(job_id: str, db: pymongo.database.Database) -> str:
    '''
    query for the poll id given a job id
    '''
    query = query_for_job_id(job_id, db)
    return [d['poll_id'] for d in query[0]['messages'] if d.get('job_id') == job_id][0]

def get_job_id_from_poll_id(poll_id: str, db: pymongo.database.Database) -> str:
    '''
    query for job id given the poll id
    '''
    query = query_for_poll_id(poll_id, db)
    return [d['job_id'] for d in query[0]['messages'] if d.get('poll_id') == poll_id][0]

def get_chat_id_from_poll_id(poll_id: str, db: pymongo.database.Database) -> int:
    '''
    query for chat id given poll id
    '''
    query = query_for_poll_id(poll_id, db)
    return query[0].get('chat_id')

def get_offending_message_id_from_poll_id(poll_id: int, db: pymongo.database.Database) -> int:
    '''
    query for message id of the message to be deleted given poll id
    '''
    query = query_for_poll_id(poll_id, db)
    return [d['offending_message_id'] for d in query[0]['messages'] if d.get('poll_id') == poll_id][0]

def get_poll_message_id_from_poll_id(poll_id: int, db: pymongo.database.Database):
    '''
    query for message id containing the poll given the poll id
    '''
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
    