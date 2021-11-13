import re, json, pymongo, uuid, pytz
from time import time as current_time
from app.constants import *
from app import database
from munch import Munch
from app.scheduler import scheduler
from telegram import ReplyKeyboardRemove
from datetime import datetime, date, timedelta, time
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP


def write_json(data: dict, fname: str) -> None:
    '''
    Utility function to pretty print json data into .json file
    '''
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def is_text_message(update: Munch) -> bool:
    '''
    returns True if there is a text message received by the bot
    '''
    return 'message' in update and 'text' in update.message


def is_private_message(update: Munch) -> bool:
    '''
    returns True if text message is sent to the bot in a private message
    '''
    return update.message.chat.type == 'private'


def is_group_message(update: Munch) -> bool:
    '''
    returns True if text message is sent in a group chat that the bot is in
    '''
    return update.message.chat.type in ['group', 'supergroup']


def is_valid_private_message_command(update: Munch) -> bool:
    '''
    returns True if a command is sent to the bot in a private chat in the form of /<command>
    '''
    text = update.message.text
    return is_private_message(update) and text in COMMANDS.keys()


def is_valid_group_message_command(update: Munch) -> bool:
    '''
    returns True if a command is sent to the bot in a group chat in the form of
    /<command>@<bot's username>
    '''
    text = update.message.text
    return is_group_message(update) and 'entities' in update.message and \
        len(update.message.entities) == 1 and \
        '@' in text and \
        text.strip().split(" ")[0].split("@")[0] in COMMANDS.keys() and \
        text.split(" ")[0].split("@")[1] == Bot.get_me().username


def is_valid_command(update: Munch) -> bool:
    '''
    returns True if a command is sent to the bot in the form of
    /<command>@<bot's username> in a group chat, or /<command> in a private message
    '''
    return is_text_message(update) and (
        is_valid_private_message_command(update)
        or is_valid_group_message_command(update))


def extract_command(update: Munch) -> str:
    '''
    Commands sent in group chat are in the form of '/<command>@<username>'. 
    This function extracts out the command and returns it as a string
    '''
    return update.message.text.strip().split(" ")[0].split("@")[0]


def is_reply_to_bot(update: Munch) -> bool:
    '''
    returns True if somebody replied to the bot's message
    '''
    return is_text_message(update) and 'reply_to_message' in update.message and \
        update.message.reply_to_message['from'].id == Bot.get_me().id


def added_to_group(update: Munch) -> bool:
    '''
    Returns True if the bot is added into a group
    '''
    return ('message' in update and \
        'new_chat_members' in update.message and \
        Bot.get_me().id in [user.id for user in update.message.new_chat_members]) or \
            group_created(update)


def removed_from_group(update: Munch) -> bool:
    '''
    Returns True if the bot is removed from a group
    '''
    return 'my_chat_member' in update and \
        'new_chat_member' in update.my_chat_member and \
        update.my_chat_member.new_chat_member.user.id == Bot.get_me().id and \
        update.my_chat_member.new_chat_member.status == 'left'


def is_callback_query(update: Munch) -> bool:
    '''
    returns True if somebody pressed on an inline keyboard button
    '''
    return 'callback_query' in update


def group_created(update: Munch) -> bool:
    '''
    returns True if a group has been created
    '''
    return 'message' in update and \
        'group_chat_created' in update.message


def group_upgraded_to_supergroup(update: Munch) -> bool:
    '''
    returns True if the group the bot is in is upgraded to a supergroup
    '''
    return 'message' in update and \
        'migrate_to_chat_id' in update.message


def get_migrated_chat_mapping(update: Munch) -> dict:
    '''
    returns a mapping of chat id to superchat id when the group chat is upgraded to superchat
    '''
    chat_id = update.message.chat.id
    supergroup_chat_id = update.message.migrate_to_chat_id
    return {"chat_id": chat_id, "supergroup_chat_id": supergroup_chat_id}


def is_valid_time(text: str) -> bool:
    '''
    Use regex to match military time in <HH>:<MM> 
    source: https://stackoverflow.com/questions/1494671/regular-expression-for-matching-time-in-military-24-hour-format
    regex: ^([01]\d|2[0-3]):?([0-5]\d)$
        ^        Start of string (anchor)
        (        begin capturing group
        [01]   a "0" or "1"
        \d     any digit
        |       or
        2[0-3] "2" followed by a character between 0 and 3 inclusive
        )        end capturing group
        :        colon
        (        start capturing
        [0-5]  character between 0 and 5
        \d     digit
        )        end group
        $        end of string anchor
    '''
    return re.fullmatch('^([01]\d|2[0-3]):([0-5]\d)$', text) is not None


def is_valid_frequency(type: str, digit: str) -> bool:
    '''
    Check if valid day of week or valid day of month
    '''
    if type == REMINDER_WEEKLY:
        digit = DAY_OF_WEEK[digit]
        return digit >= 1 and digit <= 7
    elif type == REMINDER_MONTHLY:
        try:
            digit = int(digit)
        except ValueError:
            return False
        return digit >= 1 and digit <= 31
    return False


def parse_day_of_month(day: str):
    '''
    1 -> 1st
    2 -> 2nd
    3 -> 3rd
    4 -> 4th, ...
    '''
    if int(day[1]) == 1:
        return f"{day}st"
    elif int(day[1]) == 2:
        return f"{day}nd"
    elif int(day[2]) == 3:
        return f"{day}rd"
    else:
        return f"{day}th"


def calculate_date(current_datetime: datetime, reminder_time: str):
    current_time = current_datetime.strftime("%H:%M")
    current_hour, current_minute = [int(t) for t in current_time.split(":")]
    hour, minute = [int(t) for t in reminder_time.split(":")]
    if hour < current_hour or (hour == current_hour
                               and minute < current_minute):
        return (current_datetime + timedelta(days=1)).date()
    return current_datetime.date()


def show_calendar(update: Munch, min_date: date) -> None:
    calendar, step = DetailedTelegramCalendar(min_date=min_date).build()
    Bot.send_message(update.message.chat.id,
                     f"Select {LSTEP[step]}",
                     reply_to_message_id=update.message.message_id,
                     reply_markup=calendar)


def remove_reply_keyboard_markup(update: Munch,
                                 db: pymongo.database.Database,
                                 message: str = "Removing reply keyboard...",
                                 reply_to_message: bool = True) -> None:
    '''
    Send a message to prompt for reminder text with a force reply.
    Inline keyboard to cancel command.
    '''
    if reply_to_message:
        return Bot.send_message(
            update.message.chat.id,
            message,
            reply_to_message_id=update.message.message_id,
            reply_markup=ReplyKeyboardRemove(selective=True))
    else:
        return Bot.send_message(
            update.message.chat.id,
            message,
            reply_markup=ReplyKeyboardRemove(selective=True))


def create_reminder(chat_id: int, from_user_id: int,
                    db: pymongo.database.Database) -> None:
    timezone = database.query_for_timezone(chat_id, db)
    reminder = database.get_reminder_in_construction(chat_id, from_user_id, db)
    reminder_id = str(uuid.uuid4())
    reminder['reminder_id'] = reminder_id
    job_id = str(current_time()) + "_" + reminder['reminder_text']
    reminder['job_id'] = job_id
    database.insert_reminder(chat_id, reminder, db)
    hour, minute = [int(t) for t in reminder['time'].split(":")]
    if reminder['frequency'] == REMINDER_ONCE:
        time_str = f"{reminder['frequency'].split()[1]}-{hour}-{minute}"
        run_date = pytz.timezone(timezone).localize(
            datetime.strptime(time_str, "%Y-%m-%d-%H-%M")).astimezone(pytz.utc)
    else:
        run_date = datetime.combine(datetime.today(), time(hour, minute))
        run_date = run_date.replace(day=10)
        run_date = pytz.timezone(timezone).localize(run_date).astimezone(
            pytz.utc)
    ###################################

    if REMINDER_ONCE in reminder['frequency']:
        scheduler.add_job(reminder_trigger,
                          'date',
                          run_date=run_date,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_DAILY in reminder['frequency']:
        # extract hour and minute
        print("here!")
        scheduler.add_job(reminder_trigger,
                          'cron',
                          day="*",
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_WEEKLY in reminder['frequency']:
        # TODO: extract day of week
        day = int(reminder['frequency'].split('-')[1]) - 1
        diff = run_date.weekday() - day
        run_date.replace(day=run_date.day - diff)
        scheduler.add_job(reminder_trigger,
                          'cron',
                          week="*",
                          day_of_week=run_date.weekday(),
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_MONTHLY in reminder['frequency']:
        # TODO: extract day of month
        day = int(reminder['frequency'].split('-')[1])
        scheduler.add_job(reminder_trigger,
                          'cron',
                          month="*",
                          day=day,
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)


def reminder_trigger(chat_id: int, reminder_id: str):
    with pymongo.MongoClient(database.MONGO_DATABASE_URL) as client:
        db = client[database.MONGO_DB]
        reminders = database.query_for_reminders(chat_id, db)
        reminder = [r for r in reminders if r['reminder_id'] == reminder_id][0]
        file_id = None
        if 'file_id' in reminder:
            file_id = reminder['file_id']
        if file_id is not None:
            Bot.send_photo(chat_id,
                           photo=file_id,
                           caption=f"🗓 {reminder['reminder_text']}")
        else:
            Bot.send_message(chat_id, f"🗓 {reminder['reminder_text']}")
        database.delete_reminder(chat_id, reminder_id, db)
