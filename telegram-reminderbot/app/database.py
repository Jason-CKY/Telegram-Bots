import pymongo
import os
from typing import List
from app.constants import REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY

print()
MONGO_USERNAME = os.getenv('MONGO_USERNAME')  # ; print(MONGO_USERNAME)
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')  # ; print(MONGO_PASSWORD)
MONGO_SERVER = os.getenv('MONGO_SERVER')  # ; print(MONGO_SERVER)
MONGO_PORT = os.getenv('MONGO_PORT')  # ; print(MONGO_PORT)
MONGO_DB = os.getenv('MONGO_DB')  # ; print(MONGO_DB)
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


class Database:
    '''
    General database class to store all data operations and queries
    '''
    def __init__(self, chat_id: str, db: pymongo.database.Database):
        self.db = db
        self.chat_id = chat_id
        self.chat_collection = self.db[CHAT_COLLECTION]

    '''
    Query functions
    '''

    def query_for_chat_id(self) -> List[dict]:
        '''
        Returns the chat query with messages that contains the given chat id. By right this should only
        return a list of 1 entry as chat ids are unique to each chat, but return the entire query regardless
        '''
        query = list(self.chat_collection.find({"chat_id": self.chat_id}))
        if len(query) == 0:
            raise AssertionError(
                "This group chat ID does not exist in the database!")

        return query

    def query_for_job_id(self, job_id: str) -> List[dict]:
        '''
        Returns the chat query with messages that contains the given job id. By right this should only
        return a list of 1 entry as job ids are unique to each job, but return the entire query regardless
        '''
        query = list(self.chat_collection.find({"reminders.job_id": job_id}))
        if len(query) == 0:
            raise AssertionError("No such job exists in this chat")

        return query

    def query_for_reminder_in_construction(self) -> list:
        return self.query_for_chat_id()[0]['reminders_in_construction']

    def query_for_reminders(self) -> list:
        return self.query_for_chat_id()[0]['reminders']

    def query_for_timezone(self) -> str:
        return self.query_for_chat_id()[0]['timezone']


def query_for_reminder_in_construction(chat_id: int,
                                       db: pymongo.database.Database) -> list:
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"chat_id": chat_id}))
    return query[0]['reminders_in_construction']


def query_for_reminders(chat_id: int, db: pymongo.database.Database) -> list:
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"chat_id": chat_id}))
    return query[0]['reminders']


def query_for_timezone(chat_id: int, db: pymongo.database.Database) -> str:
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"chat_id": chat_id}))
    return query[0]['timezone']


def query_for_chat_id(chat_id: int,
                      db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the chat query with messages that contains the given chat id. By right this should only
    return a list of 1 entry as chat ids are unique to each chat, but return the entire query regardless
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"chat_id": chat_id}))
    if len(query) == 0:
        raise AssertionError(
            "This group chat ID does not exist in the database!")

    return query


def query_for_job_id(job_id: str, db: pymongo.database.Database) -> List[dict]:
    '''
    Returns the chat query with messages that contains the given job id. By right this should only
    return a list of 1 entry as job ids are unique to each job, but return the entire query regardless
    '''
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"reminders.job_id": job_id}))
    if len(query) == 0:
        raise AssertionError("No such job exists in this chat")

    return query


def delete_reminder_in_construction(chat_id: int, from_user_id: int,
                                    db: pymongo.database.Database) -> None:
    chat_collection = db[CHAT_COLLECTION]
    query = list(
        chat_collection.find({
            "chat_id": chat_id,
            "reminders_in_construction.user_id": from_user_id
        }))

    if len(query) == 0:
        return

    query = query[0]['reminders_in_construction']

    reminders_in_construction = [
        q for q in query if q['user_id'] != from_user_id
    ]
    newvalues = {
        "$set": {
            "reminders_in_construction": reminders_in_construction
        }
    }
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def delete_reminder(chat_id: int, reminder_id: str,
                    db: pymongo.database.Database) -> None:
    chat_collection = db[CHAT_COLLECTION]
    query = list(
        chat_collection.find({
            "chat_id": chat_id,
            "reminders.reminder_id": reminder_id
        }))[0]['reminders']
    reminders = [q for q in query if q['reminder_id'] != reminder_id]
    newvalues = {"$set": {"reminders": reminders}}
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def is_reminder_time_in_construction(chat_id: int, from_user_id: int,
                                     db: pymongo.database.Database) -> bool:
    chat_collection = db[CHAT_COLLECTION]
    query = list(
        chat_collection.find({
            "chat_id": chat_id,
            "reminders_in_construction.user_id": from_user_id
        }))
    if len(query) == 0:
        return False
    reminders_in_construction = query[0]['reminders_in_construction']
    for reminder in reminders_in_construction:
        if reminder['user_id'] == from_user_id and "time" not in reminder:
            return True
    return False


def is_reminder_frequency_in_construction(
        chat_id: int, from_user_id: int,
        db: pymongo.database.Database) -> bool:
    possible_reminder_frequencies = [
        REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
    ]
    chat_collection = db[CHAT_COLLECTION]
    query = list(
        chat_collection.find({
            "chat_id": chat_id,
            "reminders_in_construction.user_id": from_user_id
        }))
    if len(query) == 0:
        return False
    reminders_in_construction = query[0]['reminders_in_construction']
    for reminder in reminders_in_construction:
        if reminder['user_id'] == from_user_id and "time" in reminder and (
            ('frequency' not in reminder) or
            (reminder['frequency'].split('-')[0]
             in possible_reminder_frequencies)):
            return True
    return False


def update_chat_settings(chat_id: int, db: pymongo.database.Database,
                         **kwargs):
    chat_collection = db[CHAT_COLLECTION]
    newvalues = {"$set": {k: v for k, v in kwargs.items()}}
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def update_reminder_in_construction(chat_id: int, from_user_id: int,
                                    db: pymongo.database.Database, **kwargs):
    chat_collection = db[CHAT_COLLECTION]
    reminders_in_construction = query_for_reminder_in_construction(chat_id, db)
    for reminder in reminders_in_construction:
        if reminder['user_id'] == from_user_id:
            for k, v in kwargs.items():
                reminder[k] = v
    newvalues = {
        "$set": {
            "reminders_in_construction": reminders_in_construction
        }
    }
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def is_chat_id_exists(chat_id: int, db: pymongo.database.Database) -> bool:
    chat_collection = db[CHAT_COLLECTION]
    return len(list(chat_collection.find({'chat_id': chat_id}))) != 0


def add_reminder_to_construction(chat_id: int, from_user_id: int,
                                 db: pymongo.database.Database) -> None:
    chat_collection = db[CHAT_COLLECTION]
    newvalues = {
        "$push": {
            "reminders_in_construction": {
                "user_id": from_user_id
            }
        }
    }
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def insert_reminder(chat_id: int, reminder: dict,
                    db: pymongo.database.Database) -> None:
    chat_collection = db[CHAT_COLLECTION]
    newvalues = {"$push": {"reminders": reminder}}
    chat_collection.update_one({"chat_id": chat_id}, newvalues)


def get_chat_id_from_job_id(job_id: str, db: pymongo.database.Database) -> int:
    query = query_for_job_id(job_id, db)[0]
    return query['chat_id']


def get_reminder_id_from_job_id(job_id: str,
                                db: pymongo.database.Database) -> str:
    query = query_for_job_id(job_id, db)[0]
    return [
        r['reminder_id'] for r in query['reminders'] if r['job_id'] == job_id
    ][0]


def get_reminder_in_construction(chat_id: int, from_user_id: int,
                                 db: pymongo.database.Database) -> list:
    reminders_in_construction = query_for_reminder_in_construction(chat_id, db)
    return [
        r for r in reminders_in_construction if r['user_id'] == from_user_id
    ][0]


def delete_chat_collection(chat_id: int,
                           db: pymongo.database.Database) -> List[dict]:
    '''
    Deletes the entire entry that matches the chat id. This helps to clean up the database once the bot is removed from the group
    '''
    chat_collection = db[CHAT_COLLECTION]
    chat_collection.delete_many({'chat_id': chat_id})


def add_chat_collection(chat_id: int, db: pymongo.database.Database) -> None:
    '''
    Add a new db entry with the chat id within the update json object. It is initialized
    with empty config. Call the set_chat_configs function to fill in the config with dynamic values.
    '''
    chat_collection = db[CHAT_COLLECTION]
    # delete the chat_id document if it exists
    if len(list(chat_collection.find({'chat_id': chat_id}))) != 0:
        chat_collection.delete_many({'chat_id': chat_id})

    # create a new chat_id document with default config and empty list for deleting messages
    data = {
        "chat_id": chat_id,
        "timezone": "Asia/Singapore",
        "update_settings": False,
        "reminders_in_construction": [],
        "reminders": []
    }
    x = chat_collection.insert_one(data)


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
    query = {"chat_id": mapping['chat_id']}
    newvalues = {"$set": {"chat_id": mapping['supergroup_chat_id']}}
    chat_collection.update_one(query, newvalues)
