import json, pymongo, logging, os
from app import utils
from app.command_mappings import COMMANDS
from app.scheduler import scheduler
from app.database import get_db, Database
from app.menu import ListReminderMenu, ReminderBuilder, SettingsMenu
from app.constants import Bot, PUBLIC_URL, BOT_TOKEN, DEV_CHAT_ID
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI(root_path="/reminderbot")

def process_command(update: Munch, db: pymongo.database.Database) -> None:
    database = Database(update.message.chat.id, db)
    command = utils.extract_command(update)
    return COMMANDS[command](update, database)


def callback_query_handler(update: Munch,
                           db: pymongo.database.Database) -> None:
    c = update.callback_query
    database = Database(c.message.chat.id, db)
    if c.data.startswith('cbcal'):
        ReminderBuilder(database).process_callback(c)
    elif c.data.startswith('lr'):
        '''
        list reminder callback buttons
        '''
        message, markup, parse_mode = ListReminderMenu(
            c.message.chat.id, database).process(c.data)
        Bot.edit_message_text(message,
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=markup,
                              parse_mode=parse_mode)


def process_message(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Process any messages that is a sent to the bot. This will either be a normal private message or a reply to the bot in group chats due to privacy settings turned on.
    if text is in the format of <HH>:<MM>, query the database 
    '''
    database = Database(update.message.chat.id, db)
    if not database.is_chat_id_exists():
        database.add_chat_collection()

    if update.message.text == '🚫 Cancel':
        utils.remove_reply_keyboard_markup(update,
                                           message="Operation cancelled.")
        database.delete_reminder_in_construction(update.message['from'].id)
    elif database.query_for_chat_id()[0]['update_settings']:
        SettingsMenu(update.message.chat.id,
                     database).process_message(update.message.text)
    else:
        ReminderBuilder(database).process_message(update)


@app.on_event("startup")
def startup_event():
    scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


@app.get("/")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
    }


@app.post(f"/{BOT_TOKEN}")
async def respond(request: Request,
                  db: pymongo.database.Database = Depends(get_db)):
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
        elif utils.is_text_message(update):
            # this will be a normal text message if pm, and any text messages that is a reply to bot in group due to bot privacy setting
            process_message(update, db)
        elif utils.is_callback_query(update):
            callback_query_handler(update, db)
        elif utils.added_to_group(update):
            #TODO: initiate process to set timezone
            pass

    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
        # raise

    return Response(status_code=status.HTTP_200_OK)
