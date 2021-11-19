import re, json, pymongo, uuid, pytz
from app.constants import Bot, DAY_OF_WEEK, REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
from app.command_mappings import COMMANDS
from app.database import Database, MONGO_DATABASE_URL, MONGO_DB
from app.menu import RenewReminderMenu
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


def show_calendar(update: Munch, min_date: date) -> None:
    calendar, step = DetailedTelegramCalendar(min_date=min_date).build()
    Bot.send_message(update.message.chat.id,
                     f"Select {LSTEP[step]}",
                     reply_to_message_id=update.message.message_id,
                     reply_markup=calendar)


def remove_reply_keyboard_markup(update: Munch,
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


def add_scheduler_job(reminder: dict, hour: int, minute: int, timezone: str,
                      chat_id: int, reminder_id: str, job_id: str) -> None:
    if REMINDER_ONCE in reminder['frequency']:
        time_str = f"{reminder['frequency'].split()[1]}-{hour}-{minute}"
        # run_date = pytz.timezone(timezone).localize(
        #     datetime.strptime(time_str, "%Y-%m-%d-%H-%M")).astimezone(pytz.utc)
        run_date = pytz.utc.localize(
            datetime.strptime(time_str, "%Y-%m-%d-%H-%M"))
        scheduler.add_job(reminder_trigger,
                          'date',
                          run_date=run_date,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_DAILY in reminder['frequency']:
        # extract hour and minute
        run_date = datetime.combine(datetime.today(), time(hour, minute))
        run_date = run_date.replace(day=10)
        # run_date = pytz.timezone(timezone).localize(run_date).astimezone(
        #     pytz.utc)
        run_date = pytz.utc.localize(run_date)
        scheduler.add_job(reminder_trigger,
                          'cron',
                          day="*",
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_WEEKLY in reminder['frequency']:
        day = int(reminder['frequency'].split('-')[1]) - 1
        hour, minute = [int(t) for t in convert_time_str(f"{hour}:{minute}", timezone).split(":")]
        run_date = datetime.combine(datetime.today(), time(hour, minute))
        run_date = run_date.replace(day=run_date.day - (run_date.weekday() - day))
        run_date = pytz.timezone(timezone).localize(run_date).astimezone(pytz.utc)
        scheduler.add_job(reminder_trigger,
                          'cron',
                          week="*",
                          day_of_week=run_date.weekday(),   # day of week goes from 0-6
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)
    elif REMINDER_MONTHLY in reminder['frequency']:
        day = int(reminder['frequency'].split('-')[1])
        hour, minute = [int(t) for t in convert_time_str(f"{hour}:{minute}", timezone).split(":")]
        run_date = datetime.combine(datetime.today(), time(hour, minute)).replace(day=day)
        run_date = pytz.timezone(timezone).localize(run_date).astimezone(pytz.utc)
        scheduler.add_job(reminder_trigger,
                          'cron',
                          month="*",
                          day=run_date.day,
                          hour=run_date.hour,
                          minute=run_date.minute,
                          args=[chat_id, reminder_id],
                          id=job_id)


def create_reminder(chat_id: int, from_user_id: int,
                    database: Database) -> None:
    timezone = database.query_for_timezone()
    reminder = database.get_reminder_in_construction(from_user_id)
    reminder_id = str(uuid.uuid4())
    reminder['reminder_id'] = reminder_id
    job_id = str(uuid.uuid4())
    reminder['job_id'] = job_id
    hour, minute = [int(t) for t in reminder['time'].split(":")]
    if 'timezone' not in reminder.keys():
        reminder['timezone'] = timezone
    timezone = reminder['timezone']
    add_scheduler_job(reminder, hour, minute, timezone, chat_id, reminder_id,
                      job_id)
    database.insert_reminder(reminder)


def reminder_trigger(chat_id: int, reminder_id: str) -> None:
    with pymongo.MongoClient(MONGO_DATABASE_URL) as client:
        db = client[MONGO_DB]
        database = Database(chat_id, db)
        reminder = database.get_reminder_from_reminder_id(reminder_id)
        message, markup, parse_mode = RenewReminderMenu(
            chat_id, database).build(reminder['reminder_text'],
                                     image='file_id' in reminder.keys())
        if 'file_id' in reminder:
            file_id = reminder['file_id']
            Bot.send_photo(chat_id,
                           photo=file_id,
                           caption='🖼' + message,
                           reply_markup=markup,
                           parse_mode=parse_mode)
        else:
            Bot.send_message(chat_id,
                             '🗓' + message,
                             reply_markup=markup,
                             parse_mode=parse_mode)

        if reminder['frequency'].startswith(REMINDER_ONCE):
            database.delete_reminder(reminder_id)


def extract_command(update: Munch) -> str:
    '''
    Commands sent in group chat are in the form of '/<command>@<username>'. 
    This function extracts out the command and returns it as a string
    '''
    return update.message.text.strip().split(" ")[0].split("@")[0]


def parse_day_of_month(day: str) -> str:
    '''
    1 -> 1st
    2 -> 2nd
    3 -> 3rd
    4 -> 4th, ...
    '''
    ones_digit = int(day[1]) if len(day) > 1 else int(day)
    if ones_digit == 1:
        return f"{day}st"
    elif ones_digit == 2:
        return f"{day}nd"
    elif ones_digit == 3:
        return f"{day}rd"
    else:
        return f"{day}th"


def get_migrated_chat_mapping(update: Munch) -> dict:
    '''
    returns a mapping of chat id to superchat id when the group chat is upgraded to superchat
    '''
    chat_id = update.message.chat.id
    supergroup_chat_id = update.message.migrate_to_chat_id
    return {"chat_id": chat_id, "supergroup_chat_id": supergroup_chat_id}


def convert_time_str(time_str: str, timezone: str):
    '''
    Convert UTC <HH>:<MM> into timzone specific <HH>:<MM>
    time_str: 05:22 (hour:minute)
    '''
    hour, minute = [int(t) for t in time_str.split(":")]
    return pytz.utc.localize(datetime.now()).replace(
        hour=hour,
        minute=minute).astimezone(pytz.timezone(timezone)).strftime("%H:%M")

def convert_time_str_back_to_utc(time_str: str, timezone: str):
    '''
    Convert timezone specific <HH>:<MM> into UTC <HH>:<MM>
    time_str: 05:22 (hour:minute)
    '''
    hour, minute = [int(t) for t in time_str.split(":")]
    return pytz.timezone(timezone).localize(datetime.now()).replace(
        hour=hour,
        minute=minute).astimezone(pytz.utc).strftime("%H:%M")


def calculate_date(current_datetime: datetime, reminder_time: str) -> date:
    current_time = current_datetime.strftime("%H:%M")
    current_hour, current_minute = [int(t) for t in current_time.split(":")]
    hour, minute = [int(t) for t in reminder_time.split(":")]
    if hour < current_hour or (hour == current_hour
                               and minute < current_minute):
        return (current_datetime + timedelta(days=1)).date()
    return current_datetime.date()


'''
Boolean functions
'''


def is_photo_message(update: Munch) -> bool:
    return 'message' in update and 'photo' in update.message


def is_text_message(update: Munch) -> bool:
    '''
    returns True if there is a text message received by the bot
    '''
    return 'message' in update and 'text' in update.message


def is_callback_query_with_photo(update: Munch) -> bool:
    return is_callback_query(
        update) and 'photo' in update.callback_query.message


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
