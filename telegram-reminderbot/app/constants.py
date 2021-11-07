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

# import this line to avoid importing commands before
# defining the rest of the config as commands also import
# the configs from this file

from app import commands

'''
start - Help on how to use this Bot
help - Help on how to use this Bot
delete - Reply to a message with this command to initiate poll to delete
getconfig - Get current threshold and expiry time for this group chat
setthreshold - Set a threshold for this group chat
setexpiry - Set a expiry time for the poll
support - Support me on github!
'''
COMMANDS = {
    '/start': commands.start,
    '/help': commands.start,
    '/support': commands.support,
    '/remind': commands.remind,
    '/calendar': commands.show_calendar # test function
}

# REPLY_KEYBOARD_COMMANDS = {
#     '🚫 Cancel': commands.remove_reply_keyboard_markup
# }