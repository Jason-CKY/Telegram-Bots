import json, pymongo, logging
from app import utils, commands, database
from app.scheduler import scheduler
from app.database import get_db
from app.constants import *
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI()

def process_command(update:Munch, db: pymongo.database.Database) -> None:
    command = utils.extract_command(update)
    return COMMANDS[command](update, db)

def process_message(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Process any messages that is a sent to the bot. This will either be a normal private message or a reply to the bot in group chats due to privacy settings turned on.
    if text is in the format of <HH>:<MM>, query the database 
    '''
    # command = utils.extract_command(update)
    if update.message.text == '🚫 Cancel':
        database.delete_reminder_in_construction(update.message.chat.id, update.message['from'].id)
        commands.remove_reply_keyboard_markup(update, db)
    
    # reminder text -> reminder time -> reminder frequency -> reminder set.
    if database.is_reminder_text_in_construction(update.message.chat.id, update.message['from'].id):
        # enter reminder time
        pass
    elif database.is_reminder_time_in_construction(update.message.chat.id, update.message['from'].id):
        if utils.is_valid_time(update.message.text):
            # update database
            pass
        else:
            # send error message
            pass
        pass
    # enter reminder frequency
    elif database.is_reminder_frequency_in_construction(update.message.chat.id, update.message['from'].id):
        # create reminder
        pass
    # any text received by bot with no entry in db is treated as reminder text
    else:

        pass

def callback_query_handler(update: Munch, db: pymongo.database.Database) -> None:
    c = update.callback_query
    if c.data.startswith('cbcal'):
        result, key, step = DetailedTelegramCalendar(min_date=date.today()).process(c.data)
        if not result and key:
            Bot.edit_message_text(f"Select {LSTEP[step]}",
                                        c.message.chat.id,
                                        c.message.message_id,
                                        reply_markup=key)
        elif result:
            Bot.edit_message_text(f"You selected {result}",
                                    c.message.chat.id,
                                    c.message.message_id)

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/reminderbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
        }

@app.post(f"/reminderbot/{BOT_TOKEN}")
async def respond(request:Request, db: pymongo.database.Database = Depends(get_db)):
    try:
        req = await request.body()
        update = Munch.fromDict(json.loads(req))
        utils.write_json(update, f"/code/app/output.json")

        # TODO: modify this function at the last
        # if utils.group_upgraded_to_supergroup(update): 
        #     mapping = utils.get_migrated_chat_mapping(update)
        #     database.update_chat_id(mapping, db)

        if utils.is_valid_command(update):
            process_command(update, db)
        elif utils.is_text_message(update): # this will be a normal text message if pm, and any text messages that is a reply to bot in group due to bot privacy setting
            process_message(update, db)
        elif utils.is_callback_query(update):
            callback_query_handler(update, db)
        
    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
        # raise
            
    return Response(status_code=status.HTTP_200_OK)