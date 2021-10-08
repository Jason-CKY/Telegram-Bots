from app.constants import *
from munch import Munch

def is_text_message(update: Munch):
    return 'message' in update and 'text' in update.message

def is_private_message(update:Munch):
    return update.message.chat.type == 'private'

def is_group_message(update:Munch):
    return update.message.chat.type in ['group', 'supergroup']

def is_valid_command(update:Munch):
    text = update.message.text
    return 'entities' in update.message and \
        len(update.message.entities) == 1 and \
        '@' in text and \
        text.strip().split(" ")[0].split("@")[0] in COMMANDS.keys() and \
        text.split(" ")[0].split("@")[1] == Bot.get_me().username

def extract_command(update:Munch):
    return update.message.text.strip().split(" ")[0].split("@")[0]

def added_to_group(update: Munch):
    return 'message' in update and \
        'new_chat_members' in update.message and \
        Bot.get_me().id in [user.id for user in update.message.new_chat_members]

def removed_from_group(update: Munch):
    return 'message' in update and \
        'left_chat_member' in update.message and \
        update.message.left_chat_member.id == Bot.get_me().id

def poll_updates(update: Munch):
    return 'poll' in update # updates on poll that Bot created