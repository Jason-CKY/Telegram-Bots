import os
from telegram.ext import ExtBot

BOT_TOKEN = os.getenv('BOT_TOKEN')
Bot = ExtBot(token=BOT_TOKEN)

PUBLIC_URL = os.getenv('PUBLIC_URL')
START_MESSAGE = r"I am a Bot that moderates chat groups. Just add me into a group chat and " + \
                r"give me permissions to send polls and delete messages. Summon me in the " + \
                f"group chat using '/delete@{Bot.get_me().username}' and reply to the message in question. " + \
                r"I will then send a poll to collect other members' opinions. If the number of votes " + \
                r"in favour of deleting the message >= certain threshold, I will close the poll and delete the message in question. " + \
                r"Polls are only active for the expiry time the group admin sets, and requests will need to be resent." 

POLL_EXPIRY = 120
MAX_EXPIRY = 600
MIN_EXPIRY = 10
DEV_CHAT_ID = 403432365

# import this line to avoid importing commands before
# defining the rest of the config as commands also import
# the configs from this file

from app import commands

COMMANDS = {
    '/start': commands.start,
    '/delete': commands.delete,
    '/getconfig': commands.get_config,
    '/setthreshold': commands.set_threshold,
    '/setexpiry': commands.set_expiry,
}