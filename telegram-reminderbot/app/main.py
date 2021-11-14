import json, pymongo, logging, pytz
from app import utils, database
from app.command_mappings import COMMANDS
from app.scheduler import scheduler
from app.database import get_db
from app.constants import Bot, PUBLIC_URL, BOT_TOKEN, DEV_CHAT_ID, DAY_OF_WEEK, REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from telegram import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI()


def process_command(update: Munch, db: pymongo.database.Database) -> None:
    command = utils.extract_command(update)
    return COMMANDS[command](update, db)


def callback_query_handler(update: Munch,
                           db: pymongo.database.Database) -> None:
    c = update.callback_query
    if c.data.startswith('cbcal'):
        reminder_in_construction = database.get_reminder_in_construction(
            c.message.chat.id, c['from'].id, db)
        timezone = database.query_for_timezone(c.message.chat.id, db)
        current_datetime = pytz.timezone('UTC').localize(
            datetime.now()).astimezone(pytz.timezone(timezone))
        result, key, step = DetailedTelegramCalendar(
            min_date=utils.calculate_date(
                current_datetime, reminder_in_construction['time'])).process(
                    c.data)
        if not result and key:
            Bot.edit_message_text(f"Select {LSTEP[step]}",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=key)
        elif result:
            Bot.edit_message_text(
                f"✅ Reminder set for {result}, {reminder_in_construction['time']}",
                c.message.chat.id, c.message.message_id)
            database.update_reminder_in_construction(
                c.message.chat.id,
                c['from'].id,
                db,
                frequency=" ".join([REMINDER_ONCE, str(result)]))
            utils.create_reminder(c.message.chat.id, c['from'].id, db)
            database.delete_reminder_in_construction(c.message.chat.id,
                                                     c['from'].id, db)


def process_message(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Process any messages that is a sent to the bot. This will either be a normal private message or a reply to the bot in group chats due to privacy settings turned on.
    if text is in the format of <HH>:<MM>, query the database 
    '''
    if update.message.text == '🚫 Cancel':
        utils.remove_reply_keyboard_markup(update,
                                           db,
                                           message="Operation cancelled.")
        database.delete_reminder_in_construction(update.message.chat.id,
                                                 update.message['from'].id, db)

    # reminder text -> reminder time -> reminder frequency -> reminder set.
    elif database.is_reminder_time_in_construction(update.message.chat.id,
                                                   update.message['from'].id,
                                                   db):
        if utils.is_valid_time(update.message.text):
            # update database
            database.update_reminder_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     db,
                                                     time=update.message.text)
            Bot.send_message(update.message.chat.id,
                             "Once-off reminder or recurring reminder?",
                             reply_to_message_id=update.message.message_id,
                             reply_markup=ReplyKeyboardMarkup(
                                 resize_keyboard=True,
                                 one_time_keyboard=True,
                                 selective=True,
                                 keyboard=[[
                                     KeyboardButton(REMINDER_ONCE),
                                     KeyboardButton(REMINDER_DAILY)
                                 ],
                                           [
                                               KeyboardButton(REMINDER_WEEKLY),
                                               KeyboardButton(REMINDER_MONTHLY)
                                           ], [KeyboardButton("🚫 Cancel")]]))
        else:
            # send error message
            Bot.send_message(update.message.chat.id,
                             "Failed to parse time. Please enter time again.",
                             reply_to_message_id=update.message.message_id,
                             reply_markup=ReplyKeyboardMarkup(
                                 resize_keyboard=True,
                                 one_time_keyboard=True,
                                 selective=True,
                                 input_field_placeholder=
                                 "enter reminder time in <HH>:<MM> format.",
                                 keyboard=[[KeyboardButton("🚫 Cancel")]]))
    # enter reminder frequency
    elif database.is_reminder_frequency_in_construction(
            update.message.chat.id, update.message['from'].id, db):
        reminder = database.get_reminder_in_construction(
            update.message.chat.id, update.message['from'].id, db)

        # create reminder
        if update.message.text == REMINDER_ONCE:
            utils.remove_reply_keyboard_markup(
                update,
                db,
                message="once-off reminder selected.",
                reply_to_message=False)
            database.update_reminder_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     db,
                                                     frequency=REMINDER_ONCE)
            reminder = database.get_reminder_in_construction(
                update.message.chat.id, update.message['from'].id, db)
            timezone = database.query_for_timezone(update.message.chat.id, db)
            current_datetime = pytz.timezone('UTC').localize(
                datetime.now()).astimezone(pytz.timezone(timezone))
            utils.show_calendar(update,
                                min_date=utils.calculate_date(
                                    current_datetime, reminder['time']))
        elif update.message.text == REMINDER_DAILY:
            database.update_reminder_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     db,
                                                     frequency=REMINDER_DAILY)
            reminder = database.get_reminder_in_construction(
                update.message.chat.id, update.message['from'].id, db)
            utils.remove_reply_keyboard_markup(
                update,
                db,
                message=f"✅ Reminder set for every day at {reminder['time']}",
                reply_to_message=False)
            utils.create_reminder(update.message.chat.id,
                                  update.message['from'].id, db)
            database.delete_reminder_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     db)

        elif update.message.text == REMINDER_WEEKLY:
            database.update_reminder_in_construction(update.message.chat.id,
                                                     update.message['from'].id,
                                                     db,
                                                     frequency=REMINDER_WEEKLY)
            Bot.send_message(
                update.message.chat.id,
                "Which day of week do you want to set your weekly reminder?",
                reply_to_message_id=update.message.message_id,
                reply_markup=ReplyKeyboardMarkup(
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    selective=True,
                    keyboard=[
                        [KeyboardButton("Monday"),
                         KeyboardButton("Tuesday")],
                        [
                            KeyboardButton("Wednesday"),
                            KeyboardButton("Thursday")
                        ],
                        [KeyboardButton("Friday"),
                         KeyboardButton("Saturday")],
                        [KeyboardButton("Sunday"),
                         KeyboardButton("🚫 Cancel")]
                    ]))

        elif update.message.text == REMINDER_MONTHLY:
            database.update_reminder_in_construction(
                update.message.chat.id,
                update.message['from'].id,
                db,
                frequency=REMINDER_MONTHLY)
            Bot.send_message(
                update.message.chat.id,
                "Which day of the month do you want to set your monthly reminder? (1-31)",
                reply_to_message_id=update.message.message_id,
            )

        elif reminder['frequency'] == REMINDER_WEEKLY or reminder[
                'frequency'] == REMINDER_MONTHLY:
            if utils.is_valid_frequency(reminder['frequency'],
                                        update.message.text):
                day = str(DAY_OF_WEEK[update.message.text]) if reminder[
                    'frequency'] == REMINDER_WEEKLY else update.message.text
                database.update_reminder_in_construction(
                    update.message.chat.id,
                    update.message['from'].id,
                    db,
                    frequency='-'.join([reminder['frequency'], day]))
                reminder = database.get_reminder_in_construction(
                    update.message.chat.id, update.message['from'].id, db)
                frequency = f"every {update.message.text}" if REMINDER_WEEKLY in reminder[
                    'frequency'] else f"{utils.parse_day_of_month(update.message.text)} of every month"
                utils.remove_reply_keyboard_markup(
                    update,
                    db,
                    message=
                    f"✅ Reminder set for {frequency} at {reminder['time']}",
                    reply_to_message=False)
                utils.create_reminder(update.message.chat.id,
                                      update.message['from'].id, db)
                database.delete_reminder_in_construction(
                    update.message.chat.id, update.message['from'].id, db)
            else:
                # send error message
                error_message = "Invalid day of week [1-7]" if reminder[
                    'frequency'] == REMINDER_WEEKLY else "Invalid day of month [1-31]"
                Bot.send_message(update.message.chat.id, error_message)
    # any text received by bot with no entry in db is treated as reminder text
    else:
        database.add_reminder_to_construction(update.message.chat.id,
                                              update.message['from'].id, db)
        database.update_reminder_in_construction(
            update.message.chat.id,
            update.message['from'].id,
            db,
            reminder_text=update.message.text)
        Bot.send_message(update.message.chat.id,
                         "enter reminder time in <HH>:<MM> format.",
                         reply_to_message_id=update.message.message_id,
                         reply_markup=ReplyKeyboardMarkup(
                             resize_keyboard=True,
                             one_time_keyboard=True,
                             selective=True,
                             input_field_placeholder=
                             "enter reminder time in <HH>:<MM> format.",
                             keyboard=[[KeyboardButton("🚫 Cancel")]]))


@app.on_event("startup")
def startup_event():
    scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


@app.get("/")
def root():
    return {"Hello": "World"}


@app.get("/reminderbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
    }


@app.post(f"/reminderbot/{BOT_TOKEN}")
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
        elif utils.is_text_message(
                update
        ):  # this will be a normal text message if pm, and any text messages that is a reply to bot in group due to bot privacy setting
            process_message(update, db)
        elif utils.is_callback_query(update):
            callback_query_handler(update, db)
        elif utils.added_to_group(update):
            #TODO: initiate process to set timezone
            pass

    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
        raise

    return Response(status_code=status.HTTP_200_OK)
