import pymongo, json
from app.constants import *
from app import database
from munch import Munch
from telegram.error import BadRequest
from app.scheduler import scheduler

def write_json(data: dict, fname: str) -> None:
    '''
    Utility function to pretty print json data into .json file
    '''
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_text_message(update: Munch) -> bool:
    '''
    returns True if there is a text message received by the bot
    '''
    return 'message' in update and 'text' in update.message

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
    return is_text_message(update) and (is_valid_private_message_command(update) or is_valid_group_message_command(update))

def extract_command(update: Munch) -> str:
    '''
    Commands sent in group chat are in the form of '/<command>@<username>'. 
    This function extracts out the command and returns it as a string
    '''
    return update.message.text.strip().split(" ")[0].split("@")[0]

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

def poll_updates(update: Munch) -> bool:
    '''
    returns True if there is any poll updates on polls that the Bot created
    '''
    return 'poll' in update

def is_poll_open(update: Munch) -> bool:
    '''
    returns True if the poll is still open
    '''
    return not update.poll.is_closed

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

def get_migrated_chat_mapping(update: Munch) -> dict:
    '''
    returns a mapping of chat id to superchat id when the group chat is upgraded to superchat
    '''
    chat_id = update.message.chat.id
    supergroup_chat_id = update.message.migrate_to_chat_id
    return {
        "chat_id": chat_id,
        "supergroup_chat_id": supergroup_chat_id
    }
