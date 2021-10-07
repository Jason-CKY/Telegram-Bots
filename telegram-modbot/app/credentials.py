import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', "default-userbot")
PUBLIC_URL = os.getenv('PUBLIC_URL')
START_MESSAGE = r"I am a Bot that moderates chat groups. Just add me into a group chat and " + \
                r"give me permissions to send polls and delete messages. Summon me in the " + \
                r"group chat using '/delete@Jason_ModBot' and reply to the message in question. " + \
                r"I will then send a poll to collect other members' opinions. If the number of votes " + \
                r"in favour of deleting the message >= certain threshold, I will close the poll and delete the message in question. " + \
                r"Polls are only active for the expiry time the group admin sets, and requests will need to be resent." 
COMMANDS = ['/start', '/delete', '/getconfig', '/setthreshold', '/setexpiry']
POLL_EXPIRY = 600