import json, pymongo, pytz
from datetime import datetime, time
from munch import Munch
from app.constants import DAY_OF_WEEK, SUPPORT_MESSAGE, START_MESSAGE, Bot, REMINDER_ONCE, REMINDER_DAILY, REMINDER_WEEKLY, REMINDER_MONTHLY
from app import database, utils
from telegram import ReplyKeyboardMarkup, KeyboardButton

# https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568


def start(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send START_MESSAGE (str) on the /start command,
    TODO: if no settings are found for current user, initiate the process to change settings
    '''
    Bot.send_message(update.message.chat.id, START_MESSAGE)


def support(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send SUPPORT_MESSAGE (str) on the /support command
    '''
    Bot.send_message(update.message.chat.id, SUPPORT_MESSAGE)


def remind(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send a message to prompt for reminder text with a force reply.
    Inline keyboard to cancel command.
    '''
    message = "Please enter reminder text. This bot allows for image reminders as well. Just attach an image and put your reminder text as the caption."
    # use ForceReply instead of ReplyKeyboardMarkup due to reply not showing on phone telegram
    # Bot.send_message(update.message.chat.id, message, reply_to_message_id=update.message.message_id,
    #     reply_markup=ForceReply(
    #         input_field_placeholder="Enter reminder text",
    #         selective=True
    #     ))
    Bot.send_message(update.message.chat.id,
                     message,
                     reply_to_message_id=update.message.message_id,
                     reply_markup=ReplyKeyboardMarkup(
                         resize_keyboard=True,
                         one_time_keyboard=True,
                         selective=True,
                         input_field_placeholder="Enter reminder text",
                         keyboard=[[KeyboardButton("🚫 Cancel")]]))


def list_reminders(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send a message listing all current reminders in the current chat group
    '''
    reminders = database.query_for_reminders(update.message.chat.id, db)
    timezone = database.query_for_timezone(update.message.chat.id, db)
    print(json.dumps(reminders, indent=4))
    message = ""
    for num, reminder in enumerate(reminders):
        hour, minute = [int(t) for t in reminder['time'].split(":")]
        if reminder['frequency'].split()[0] == REMINDER_ONCE:
            time_str = f"{reminder['frequency'].split()[1]}-{hour}-{minute}"
            run_date = pytz.timezone(timezone).localize(
                datetime.strptime(time_str, "%Y-%m-%d-%H-%M"))
            _time = run_date.strftime("%a, %-d %B %Y at %H:%M")
        elif reminder['frequency'].split('-')[0] == REMINDER_DAILY:
            reminder_time = time(hour, minute).strftime("%H:%M")
            _time = f"everyday at {reminder_time}"
        elif reminder['frequency'].split('-')[0] == REMINDER_WEEKLY:
            day_of_week = int(reminder['frequency'].split('-')[1])
            for k, v in DAY_OF_WEEK.items():
                if day_of_week == v:
                    day_of_week = k
            run_date = datetime.combine(datetime.today(), time(hour, minute))
            run_date = pytz.timezone(timezone).localize(run_date)
            reminder_time = time(hour, minute).strftime("%H:%M")
            _time = f"every {k} at {reminder_time}"
        elif reminder['frequency'].split('-')[0] == REMINDER_MONTHLY:
            day_of_month = utils.parse_day_of_month(
                reminder['frequency'].split('-')[1])
            reminder_time = time(hour, minute).strftime("%H:%M")
            _time = f"{day_of_month} of every month at {reminder_time}"

        message += f"{num+1}) {reminder['reminder_text']} ({_time}) \n"

    Bot.send_message(update.message.chat.id, message)
