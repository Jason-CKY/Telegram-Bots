from munch import Munch
from app.constants import Bot, START_MESSAGE

def start(update: Munch):
    '''
    What to print on the /start command
    '''
    Bot.send_message(update.message.chat.id, START_MESSAGE)

def delete(update: Munch):
    pass

def get_config(update: Munch):
    pass

def set_threshold(update: Munch):
    pass

def set_expiry(update: Munch):
    pass