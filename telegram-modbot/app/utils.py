from app.constants import *
from app import database
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
    return ('message' in update and \
        'new_chat_members' in update.message and \
        Bot.get_me().id in [user.id for user in update.message.new_chat_members]) or \
            group_created(update)

def removed_from_group(update: Munch):
    return 'my_chat_member' in update and \
        'new_chat_member' in update.my_chat_member and \
        update.my_chat_member.new_chat_member.user.id == Bot.get_me().id and \
        update.my_chat_member.new_chat_member.status == 'left'           

def poll_updates(update: Munch):
    return 'poll' in update # updates on poll that Bot created

def is_poll_open(update: Munch):
    return not update.poll.is_closed

def supergroup_created(update: Munch):
    return 'message' in update and \
        'supergroup_chat_created' in update.message

def group_created(update: Munch):
    return 'message' in update and \
        'group_chat_created' in update.message

def group_upgraded_to_supergroup(update: Munch):
    return 'message' in update and \
        'migrate_to_chat_id' in update.message

def get_migrated_chat_mapping(update: Munch):
    chat_id = update.message.chat.id
    supergroup_chat_id = update.message.migrate_to_chat_id
    return {
        "chat_id": chat_id,
        "supergroup_chat_id": supergroup_chat_id
    }

def get_default_chat_configs(update: Munch):
    '''
    Get default expiryTime and threshold.
    Return
        chat_config (Dict): {
            "expiryTime": POLL_EXPIRY
            "threshold": half the number of members in the group
        }
    '''
    num_members = Bot.get_chat_member_count(update.message.chat.id)
    return {
        "expiryTime": POLL_EXPIRY,
        "threshold": int(num_members/2)
    }

def get_config_message(threshold: int, expiryTime: int):
    return f"Current Group Configs:\n\tThreshold:{threshold}\n\tExpiry:{expiryTime}"

def get_initialise_config_message(chat_config: dict):
    return f"This chat is not within my database, initialising database with the following config. \n" + \
            get_config_message(chat_config['threshold'], chat_config['expiryTime']) + '\n' +\
            CONFIG_COMMAND_MESSAGE

def get_group_first_message(chat_config: dict):
    return f"{START_MESSAGE}\n\nThe default threshold is half the number of members in this group ({chat_config['threshold']}), " +\
                f"and default expiration time is {chat_config['expiryTime']} seconds before poll times out.\n" +\
                CONFIG_COMMAND_MESSAGE

def settle_poll(poll_id: str):
    client = database.get_client()
    db = client[database.MONGO_DB]
    chat_id = database.get_chat_id_from_poll_id(poll_id, db)
    poll_message_id = database.get_poll_message_id_from_poll_id(poll_id, db)
    offending_message_id = database.get_offending_message_id_from_poll_id(poll_id, db)
    Bot.stop_poll(chat_id, poll_message_id)
    database.remove_message_from_db(chat_id, offending_message_id, db)
    Bot.send_message(chat_id, "Threshold votes not reached before poll expiry.")
    client.close()