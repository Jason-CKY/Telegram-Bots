import json, pymongo, logging, uuid
from starlette.status import HTTP_201_CREATED
from app import utils, schemas
from app.command_mappings import COMMANDS
from app.scheduler import scheduler
from app.database import get_db, Database
from app.menu import ListReminderMenu, ReminderBuilder, RenewReminderMenu, SettingsMenu
from app.constants import REMINDER_DAILY, REMINDER_MONTHLY, REMINDER_ONCE, REMINDER_WEEKLY, Bot, PUBLIC_URL, BOT_TOKEN, DEV_CHAT_ID, DEFAULT_SETTINGS_MESSAGE
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
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
    elif c.data.startswith('renew'):
        message, markup, parse_mode = RenewReminderMenu(
            c.message.chat.id, database).process(c)
        if 'file_id' in update.callback_query.message:
            Bot.edit_message_caption(c.message.chat.id,
                                     c.message.message_id,
                                     caption=message,
                                     reply_markup=markup,
                                     parse_mode=parse_mode)
        else:
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
        database.update_chat_settings(update_settings=False)
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


@app.post(f"/{BOT_TOKEN}/reminders",
          response_model=schemas.ShowReminder,
          status_code=HTTP_201_CREATED)
async def insert_reminder(request: schemas.Reminder,
                          db: pymongo.database.Database = Depends(get_db)):
    if not utils.is_valid_time(request.time):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Invalid time!")
    if request.frequency.split()[0].split('-')[0] not in [
            REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
    ]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=
            f"Invalid frequency. Use either {REMINDER_ONCE}, {REMINDER_DAILY}, {REMINDER_WEEKLY} or {REMINDER_MONTHLY}"
        )
    database = Database(request.chat_id, db)

    if not database.is_chat_id_exists():
        database.add_chat_collection()
        timezone = request.timezone if request.timezone is not None else 'Asia/Singapore'
        database.update_chat_settings(timezone=timezone)

    request = Munch.fromDict(request.dict())
    if request.file_id is None:
        del request.file_id
    request.reminder_id = str(uuid.uuid4())
    request.job_id = str(uuid.uuid4())
    _reminder = request.copy()
    if 'timezone' in _reminder.keys():
        del _reminder['timezone']
    del _reminder['chat_id']
    database.add_reminder_to_construction(**_reminder)
    utils.create_reminder(request.chat_id, request.from_user_id, database)
    database.delete_reminder_in_construction(request.from_user_id)
    return request


@app.post(f"/{BOT_TOKEN}")
async def respond(request: Request,
                  db: pymongo.database.Database = Depends(get_db)):
    try:
        req = await request.body()
        update = Munch.fromDict(json.loads(req))
        utils.write_json(update, f"/code/app/output.json")

        if utils.group_upgraded_to_supergroup(update):
            mapping = utils.get_migrated_chat_mapping(update)
            database = Database(None, db)
            database.update_chat_id(mapping)

        if utils.is_photo_message(update):
            update.message.file_id = update.message.photo[-1]['file_id']
            update.message.text = '' if 'caption' not in update.message else update.message.caption
            del update.message.photo
            if 'caption' in update.message:
                del update.message.caption
        if utils.is_callback_query_with_photo(update):
            update.callback_query.message.file_id = update.callback_query.message.photo[
                -1]['file_id']
            update.callback_query.message.text = update.callback_query.message.caption
            del update.callback_query.message.photo
            del update.callback_query.message.caption

        if utils.is_valid_command(update):
            database = Database(update.message.chat.id, db)
            try:
                database.query_for_chat_id()
            except AssertionError:
                Bot.send_message(update.message.chat.id,
                                 DEFAULT_SETTINGS_MESSAGE)
            process_command(update, db)
        elif utils.is_text_message(update):
            # this will be a normal text message if pm, and any text messages that is a reply to bot in group due to bot privacy setting
            process_message(update, db)
        elif utils.is_callback_query(update):
            callback_query_handler(update, db)

    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
        raise

    return Response(status_code=status.HTTP_200_OK)
