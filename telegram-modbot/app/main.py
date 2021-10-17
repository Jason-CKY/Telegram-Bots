import json, pymongo, logging
from app import utils, commands, database
from app.scheduler import scheduler
from app.database import get_db
from app.constants import *
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch
from telegram.error import BadRequest

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def initialise_configs_if_not_exists(update: Munch, db: pymongo.database.Database):
    '''
    Triggered when a message is sent in a group the bot is in. Checks for the chat id within mongodb for configs,
    and creates the chat collection with default configs if it does not exists.
    '''
    if database.config_exists(update.message.chat.id, db):
        database.add_chat_collection(update, db)
        # send message stating the default calculated threshold and how to change it for administrators
        chat_config = utils.get_default_chat_configs(update)
        database.set_chat_configs(update, db, chat_config)

        msg = utils.get_initialise_config_message(chat_config)
        Bot.send_message(update.message.chat.id, msg)

def process_command(update:Munch, db: pymongo.database.Database):
    command = utils.extract_command(update)
    return COMMANDS[command](update, db)

def process_private_message(update:Munch, db: pymongo.database.Database):
    text = update.message.text
    if text == '/start':
        commands.start(update, db)
    else:
        msg = "Commands only work on group chats."
        Bot.send_message(update.message.chat.id, msg)

@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/modbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
        }

@app.post(f"/modbot/{BOT_TOKEN}")
async def respond(request:Request, db: pymongo.database.Database = Depends(get_db)):
    try:
        req = await request.body()
        update = json.loads(req)
        update = Munch.fromDict(update)
        write_json(update, f"/code/app/output.json")
        # TODO: find a way to schedule tasks
        if utils.group_upgraded_to_supergroup(update): 
            mapping = utils.get_migrated_chat_mapping(update)
            database.update_chat_id(mapping, db)

        elif utils.is_text_message(update):
            print("processing a message")
            initialise_configs_if_not_exists(update, db)
            if utils.is_private_message(update):
                process_private_message(update, db)
            elif utils.is_group_message(update) and utils.is_valid_command(update):
                print("processing command")
                process_command(update, db)
        
        elif utils.added_to_group(update):
            database.add_chat_collection(update, db)
            # send message stating the default calculated threshold and how to change it for administrators
            chat_config = utils.get_default_chat_configs(update)
            database.set_chat_configs(update, db, chat_config)
            msg = utils.get_group_first_message(chat_config)
            Bot.send_message(update.message.chat.id, msg)
        
        elif utils.removed_from_group(update):
            database.delete_chat_collection(update.my_chat_member.chat.id, db)
        
        elif utils.poll_updates(update) and utils.is_poll_open(update):
            chat_id = database.get_chat_id_from_poll_id(update.poll.id, db)
            _, threshold = database.get_config(chat_id, db)
            delete_count = [d for d in update.poll.options if d.get('text') == 'Delete'][0].get('voter_count')
            if delete_count >= threshold:
                utils.settle_poll(update.poll.id, expired=False)
    
    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
            
    return Response(status_code=status.HTTP_200_OK)