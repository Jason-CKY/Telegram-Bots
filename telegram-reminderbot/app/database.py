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

    def query_for_reminder_id(self, reminder_id: str) -> List[dict]:
        '''
        Returns the chat query with messages that contains the given reminder id. By right this should only
        return a list of 1 entry as job ids are unique to each job, but return the entire query regardless
        '''
        query = list(self.chat_collection.find({"reminders.reminder_id": reminder_id}))
        if len(query) == 0:
            raise AssertionError("No such job exists in this chat")
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

    def query_for_reminders_in_construction(self) -> list:
        return self.query_for_chat_id()[0]['reminders_in_construction']

    def query_for_reminders(self) -> list:
        return self.query_for_chat_id()[0]['reminders']

    def query_for_timezone(self) -> str:
        return self.query_for_chat_id()[0]['timezone']

    def get_chat_id_from_job_id(self, job_id: str) -> int:
        return self.query_for_job_id(job_id)[0]['chat_id']

    def get_reminder_id_from_job_id(self, job_id: str) -> str:
        query = self.query_for_job_id(job_id)[0]
        return [
            r['reminder_id'] for r in query['reminders']
            if r['job_id'] == job_id
        ][0]

    def get_reminder_from_reminder_id(self, reminder_id: str) -> dict:
        return [
            r for r in self.query_for_reminders()
            if r['reminder_id'] == reminder_id
        ][0]

    def get_reminder_in_construction(self, from_user_id: int) -> list:
        reminders_in_construction = self.query_for_reminders_in_construction()
        reminder_in_construction = [r for r in reminders_in_construction if r['user_id'] == from_user_id]
        if reminder_in_construction == []:
            return []
        return reminder_in_construction[0]

    '''
    Boolean functions
    '''
    def is_reminder_text_in_construction(self, from_user_id: int) -> bool:
        reminder_in_construction = self.get_reminder_in_construction(
            from_user_id)
        if reminder_in_construction == []:
            return False
        return 'reminder_text' not in reminder_in_construction

    def is_reminder_time_in_construction(self, from_user_id: int) -> bool:
        reminder_in_construction = self.get_reminder_in_construction(
            from_user_id)
        if reminder_in_construction == []:
            return False
        return 'time' not in reminder_in_construction

    def is_reminder_frequency_in_construction(self, from_user_id: int) -> bool:
        possible_reminder_frequencies = [
            REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
        ]
        reminder_in_construction = self.get_reminder_in_construction(
            from_user_id)
        if reminder_in_construction == []:
            return False

        return 'time' in reminder_in_construction and (
            ('frequency' not in reminder_in_construction) or
            (reminder_in_construction['frequency'].split('-')[0]
             in possible_reminder_frequencies))

    def is_chat_id_exists(self) -> bool:
        return len(list(self.chat_collection.find({'chat_id': self.chat_id
                                                   }))) != 0

    '''
    Insert operations
    '''

    def insert_reminder(self, reminder: dict) -> None:
        newvalues = {"$push": {"reminders": reminder}}
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def add_reminder_to_construction(self, from_user_id: int,
                                     **kwargs) -> None:
        reminder_in_construction = {"user_id": from_user_id}
        for k, v in kwargs.items():
            reminder_in_construction[k] = v

        newvalues = {
            "$push": {
                "reminders_in_construction": reminder_in_construction
            }
        }
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def add_chat_collection(self) -> None:
        '''
        Add a new db entry with the chat id within the update json object. It is initialized
        with empty config. Call the set_chat_configs function to fill in the config with dynamic values.
        '''
        # delete the chat_id document if it exists
        if self.is_chat_id_exists():
            self.chat_collection.delete_many({'chat_id': self.chat_id})

        # create a new chat_id document with default config and empty list for deleting messages
        data = {
            "chat_id": self.chat_id,
            "timezone": "Asia/Singapore",
            "update_settings": False,
            "reminders_in_construction": [],
            "reminders": []
        }
        self.chat_collection.insert_one(data)

    '''
    Update operations
    '''

    def update_chat_settings(self, **kwargs):
        newvalues = {"$set": {k: v for k, v in kwargs.items()}}
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def update_reminder_in_construction(self, from_user_id: int, **kwargs):
        reminders_in_construction = self.query_for_reminders_in_construction()
        for reminder in reminders_in_construction:
            if reminder['user_id'] == from_user_id:
                for k, v in kwargs.items():
                    reminder[k] = v
        newvalues = {
            "$set": {
                "reminders_in_construction": reminders_in_construction
            }
        }
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def update_chat_id(self, mapping: dict):
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
        query = {"chat_id": mapping['chat_id']}
        newvalues = {"$set": {"chat_id": mapping['supergroup_chat_id']}}
        self.chat_collection.update_one(query, newvalues)

    '''
    Delete operations
    '''

    def delete_reminder_in_construction(self, from_user_id: int) -> None:
        query = self.query_for_reminders_in_construction()
        reminders_in_construction = [
            q for q in query if q['user_id'] != from_user_id
        ]
        newvalues = {
            "$set": {
                "reminders_in_construction": reminders_in_construction
            }
        }
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def delete_reminder(self, reminder_id: str) -> None:
        query = self.query_for_reminders()
        reminders = [q for q in query if q['reminder_id'] != reminder_id]
        newvalues = {"$set": {"reminders": reminders}}
        self.chat_collection.update_one({"chat_id": self.chat_id}, newvalues)

    def delete_chat_collection(self) -> List[dict]:
        '''
        Deletes the entire entry that matches the chat id. This helps to clean up the database once the bot is removed from the group
        '''
        self.chat_collection.delete_many({'chat_id': self.chat_id})
