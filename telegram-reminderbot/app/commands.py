import pymongo, time, random
from datetime import datetime, timedelta
from munch import Munch
from app.constants import SUPPORT_MESSAGE, START_MESSAGE, DEV_CHAT_ID, Bot
from app.database import CHAT_COLLECTION, MIN_EXPIRY, MAX_EXPIRY
from app.scheduler import scheduler
from app import database, utils

def start(update: Munch, db: pymongo.database.Database):
    '''
    What to print on the /start command
    '''
    Bot.send_message(update.message.chat.id, START_MESSAGE)

def support(update: Munch, db: pymongo.database.Database):
    Bot.send_message(update.message.chat.id, SUPPORT_MESSAGE)

def delete(update: Munch, db: pymongo.database.Database):
    if 'reply_to_message' not in update.message:
        Bot.send_message(update.message.chat.id, "Please make sure to reply to the offending message when making request to delete.")
    else:
        # 1) check if message already exists in database
        #       send back message replying to the already in place poll if poll already exist
        if database.is_poll_exists(update, db):
            poll_message_id = database.get_poll_message_id(update, db)
            Bot.send_message(update.message.chat.id, "There is already a poll in place for the offending message", reply_to_message_id=poll_message_id)
        # 2) if no existing poll, create poll
        else:
            expiry, threshold = database.get_config(update.message.chat.id, db)
            question = f'Poll to delete the message above. This poll will last for {expiry} seconds, ' + \
                            f'if >={threshold} of the group members vote to delete within {expiry} seconds, the replied' + \
                            f'message shall be deleted.'
            
            kwargs = {
                "question": question,
                "options": ["Delete", "Don't Delete"],
                'reply_to_message_id': update.message.reply_to_message.message_id
            }
            message = Bot.send_poll(update.message.chat.id, **kwargs)
            job_id = str(update.message.chat.id) + str(random.randint(0, 10)) + str(datetime.now())
            scheduler.add_job(utils.settle_poll, 'date', run_date=datetime.now() + timedelta(seconds=expiry), args=[message.poll.id], id=job_id)
            poll_data = {
                "poll_id": message.poll.id,
                "poll_message_id": message.message_id,
                "offending_message_id": update.message.reply_to_message.message_id,
                "started_at": time.time(),
                'job_id': job_id
            }
            database.insert_chat_poll(update, poll_data, db)
            
def get_config(update: Munch, db: pymongo.database.Database):
    chat_collection = db[CHAT_COLLECTION]
    query = list(chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1}))
    if len(query) == 0:
        Bot.send_message(DEV_CHAT_ID, f"Can't find config for group chat id: {update.message.chat.id}")
        return
    config = query[0]['config']
    msg = utils.get_config_message(config['threshold'], config['expiryTime'])
    Bot.send_message(update.message.chat.id, msg)

def set_threshold(update: Munch, db: pymongo.database.Database):
    if update.message['from'].id not in [user.user.id for user in Bot.get_chat_administrators(update.message.chat.id)]:
        Bot.send_message(update.message.chat.id, "Only chat administrators allowed to set configs")
        return
    if (len(update.message.text.strip().split(" ")) == 2 and update.message.text.strip().split(" ")[1].lstrip('-').isdigit()):
        threshold = int(update.message.text.strip().split(" ")[1])
        print(threshold)
        if threshold > Bot.get_chat_member_count(update.message.chat.id):
            Bot.send_message(update.message.chat.id, f"Invalid threshold {threshold} more than members in the group.")
        elif threshold < 1:
            Bot.send_message(update.message.chat.id, f"Invalid threshold cannot be less than 1.")
        else:
            chat_collection = db[CHAT_COLLECTION]
            chat_config = chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1})[0]['config']    
            chat_config['threshold'] = threshold
            database.set_chat_configs(update, db, chat_config)
            Bot.send_message(update.message.chat.id, f"threshold set as {threshold}")

def set_expiry(update: Munch, db: pymongo.database.Database):
    if update.message['from'].id not in [user.user.id for user in Bot.get_chat_administrators(update.message.chat.id)]:
        Bot.send_message(update.message.chat.id, "Only chat administrators allowed to set configs")
        return
    if (len(update.message.text.strip().split(" ")) == 2 and update.message.text.strip().split(" ")[1].lstrip('-').isdigit()):
        expiry = int(update.message.text.strip().split(" ")[1])
        if expiry > MAX_EXPIRY:
            Bot.send_message(update.message.chat.id, f"Expiry cannot be more than {MAX_EXPIRY} seconds.")
        elif expiry < MIN_EXPIRY:
            Bot.send_message(update.message.chat.id, f"Invalid threshold cannot be less than {MIN_EXPIRY} seconds.")
        else:
            chat_collection = db[CHAT_COLLECTION]
            chat_config = chat_collection.find({"chat_id": update.message.chat.id}, {"_id": 0, "config": 1})[0]['config']    
            chat_config['expiryTime'] = expiry
            database.set_chat_configs(update, db, chat_config)
            Bot.send_message(update.message.chat.id, f"expiry set as {expiry}")