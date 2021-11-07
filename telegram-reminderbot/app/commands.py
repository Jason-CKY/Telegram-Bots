import pymongo
from munch import Munch
from app.constants import SUPPORT_MESSAGE, START_MESSAGE, DEV_CHAT_ID, Bot
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
    Bot.send_message(update.message.chat.id, message, reply_to_message_id=update.message.message_id, 
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True,
            input_field_placeholder="Enter reminder text",
            keyboard=[[KeyboardButton("🚫 Cancel")]]
        ))
