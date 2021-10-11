import pymongo
from munch import Munch
from app.constants import Bot, START_MESSAGE
from app.database import CHAT_COLLECTION, MIN_EXPIRY, MAX_EXPIRY
from app import database

def start(update: Munch, db: pymongo.database.Database):
    '''
    What to print on the /start command
    '''
    Bot.send_message(update.message.chat.id, START_MESSAGE)

def delete(update: Munch, db: pymongo.database.Database):
    pass

def get_config(update: Munch, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    config = chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1})[0]['config']
    msg = f"Current Group Configs:\n\tThreshold:{config['threshold']}\n\tExpiry:{config['expiryTime']}"
    Bot.send_message(update.message.chat.id, msg)

def set_threshold(update: Munch, db: pymongo.database.Database):
    if (update.message.text.strip().split(" ") == 2 and update.message.text.strip().split(" ")[1].isdigit()):
        threshold = int(update.message.text.strip().split(" ")[1])
        if threshold > Bot.get_chat_member_count(update.message.chat.id):
            Bot.send_message(update.message.chat.id, f"Invalid threshold {threshold} more than members in the group.")
        elif threshold < 0:
            Bot.send_message(update.message.chat.id, f"Invalid threshold cannot be less than 0.")
        
        else:
            chat_collection = db[CHAT_COLLECTION]
            chat_config = chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1})[0]['config']    
            chat_config['threshold'] = threshold
            database.update_chat_configs(update, db, chat_config)
            Bot.send_message(update.message.chat.id, f"threshold set as {threshold}")

def set_expiry(update: Munch, db: pymongo.database.Database):
    if (update.message.text.strip().split(" ") == 2 and update.message.text.strip().split(" ")[1].isdigit()):
        expiry = int(update.message.text.strip().split(" ")[1])
        if expiry > MAX_EXPIRY:
            Bot.send_message(update.message.chat.id, f"Expiry cannot be more than {MAX_EXPIRY} seconds.")
        elif expiry < MIN_EXPIRY:
            Bot.send_message(update.message.chat.id, f"Invalid threshold cannot be less than {MIN_EXPIRY} seconds.")
        else:
            chat_collection = db[CHAT_COLLECTION]
            chat_config = chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1})[0]['config']    
            chat_config['expiryTime'] = expiry
            database.update_chat_configs(update, db, chat_config)
            Bot.send_message(update.message.chat.id, f"expiry set as {expiry}")