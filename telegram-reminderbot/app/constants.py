import os
from telegram.ext import ExtBot

BOT_TOKEN = os.getenv('BOT_TOKEN')
Bot = ExtBot(token=BOT_TOKEN)

PUBLIC_URL = os.getenv('PUBLIC_URL')

START_MESSAGE = f"This bot lets you set reminders! The following commands are available:\n" +\
                f"/remind sets a reminder.\n" +\
                f"/list displays all the reminders in the current chat.\n" +\
                f"/delete deletes a reminder.\n\n\n" +\
                f"Note that all reminders set on this bot can be accessed by the user hosting this bot. Do not set any reminders that contain any sort of private information."

SUPPORT_MESSAGE =   f"My source code is hosted on https://github.com/Jason-CKY/Telegram-Bots/tree/main. Consider \n" +\
                    f"Post any issues with this bot on the github link, and feel free to contribute to the source code with a " +\
                    f"pull request."

DEV_CHAT_ID = os.getenv('DEV_CHAT_ID')

DAY_OF_WEEK = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 7
}

REMINDER_ONCE = 'Once'
REMINDER_DAILY = 'Daily'
REMINDER_WEEKLY = 'Weekly'
REMINDER_MONTHLY = 'Monthly'