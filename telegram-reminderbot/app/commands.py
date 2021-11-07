import pymongo, time, random
from datetime import datetime, timedelta
from munch import Munch
from app.constants import SUPPORT_MESSAGE, START_MESSAGE, DEV_CHAT_ID, Bot
from app.database import CHAT_COLLECTION
from app.scheduler import scheduler
from app import database, utils
from telegram import ForceReply, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date

def start(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send START_MESSAGE (str) on the /start command
    '''
    Bot.send_message(update.message.chat.id, START_MESSAGE)

def support(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send SUPPORT_MESSAGE (str) on the /support command
    '''
    Bot.send_message(update.message.chat.id, SUPPORT_MESSAGE)

def show_calendar(update: Munch, db: pymongo.database.Database) -> None:
    calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
    Bot.send_message(update.message.chat.id,
                     f"Select {LSTEP[step]}",
                     reply_markup=calendar)

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
    Bot.send_message(update.message.chat.id, message, reply_to_message_id=update.message.message_id, 
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True,
            input_field_placeholder="Enter reminder text",
            keyboard=[[KeyboardButton("🚫 Cancel")]]
        ))

def remove_reply_keyboard_markup(update: Munch, db: pymongo.database.Database) -> None:
    '''
    Send a message to prompt for reminder text with a force reply.
    Inline keyboard to cancel command.
    '''
    message = "Operation cancelled."
    Bot.send_message(update.message.chat.id, message, reply_to_message_id=update.message.message_id, 
        reply_markup=ReplyKeyboardRemove(selective=True))