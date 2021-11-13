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


def is_valid_command(update: Munch) -> bool:
    '''
    returns True if a command is sent to the bot in a group chat in the form of
    /<command>@<bot's username>
    '''
    text = update.message.text
    return 'entities' in update.message and \
        len(update.message.entities) == 1 and \
        '@' in text and \
        text.strip().split(" ")[0].split("@")[0] in COMMANDS.keys() and \
        text.split(" ")[0].split("@")[1] == Bot.get_me().username


def extract_command(update: Munch) -> str:
    '''
    Commands sent in group chat are in the form of '/<command>@<username>'. 
    This function extracts out the command and returns it as a string
    '''
    return update.message.text.strip().split(" ")[0].split("@")[0]


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
    return {"chat_id": chat_id, "supergroup_chat_id": supergroup_chat_id}


def get_default_chat_configs(update: Munch) -> dict:
    '''
    Get default expiryTime and threshold.
    Return
        chat_config (Dict): {
            "expiryTime": POLL_EXPIRY
            "threshold": half the number of members in the group
        }
    '''
    num_members = Bot.get_chat_member_count(update.message.chat.id)
    return {"expiryTime": POLL_EXPIRY, "threshold": int(num_members / 2)}


def get_config_message(threshold: int, expiryTime: int) -> str:
    '''
    return the current chat configs in a formatted string
    '''
    return f"Current Group Configs:\n\tThreshold:{threshold}\n\tExpiry:{expiryTime}"


def get_initialise_config_message(chat_config: dict) -> str:
    '''
    return the message to send if bot received message from a group chat that wasn't added to its database
    '''
    return f"This chat is not within my database, initialising database with the following config. \n" + \
            get_config_message(chat_config['threshold'], chat_config['expiryTime']) + '\n' +\
            CONFIG_COMMAND_MESSAGE


def get_group_first_message(chat_config: dict) -> str:
    '''
    return message to send when first added into group
    '''
    return f"{START_MESSAGE}\n\nThe default threshold is half the number of members in this group ({chat_config['threshold']}), " +\
                f"and default expiration time is {chat_config['expiryTime']} seconds before poll times out.\n" +\
                CONFIG_COMMAND_MESSAGE


def settle_poll(poll_id: str, expired: bool = True) -> None:
    '''
    stops the poll and count the number of votes to delete. If number of votes to delete exceed the designated threshold,
    delete the offending message. Also removes the message from the Bot's database.
    '''
    with pymongo.MongoClient(database.MONGO_DATABASE_URL) as client:
        db = client[database.MONGO_DB]
        chat_id = database.get_chat_id_from_poll_id(poll_id, db)
        job_id = database.get_job_id_from_poll_id(poll_id, db)
        poll_message_id = database.get_poll_message_id_from_poll_id(
            poll_id, db)
        offending_message_id = database.get_offending_message_id_from_poll_id(
            poll_id, db)
        _, threshold = database.get_config(chat_id, db)
        database.remove_message_from_db(chat_id, offending_message_id, db)
        first_msg = "Poll expired. Stopping poll and counting votes..." if expired else "Threshold reached."

        if not expired:
            scheduler.remove_job(job_id)

        message = Bot.send_message(chat_id, first_msg)
        try:
            poll_results = Bot.stop_poll(chat_id, poll_message_id)
        except BadRequest as e:
            error_msg = getattr(e, 'message', str(e))
            Bot.edit_message_text(chat_id=chat_id,
                                  message_id=message.message_id,
                                  text=error_msg)
            return
        delete_count = [
            d.voter_count for d in poll_results.options if d.text == 'Delete'
        ][0]
        if delete_count >= threshold:
            try:
                Bot.delete_message(chat_id, offending_message_id)
                Bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    text="Offending message has been deleted.")
            except BadRequest as e:
                error_msg = getattr(e, 'message', str(e))
                if "Message can't be deleted" in error_msg:
                    error_msg += "\nPlease check if I have permission to delete group messages."
                Bot.edit_message_text(chat_id=chat_id,
                                      message_id=message.message_id,
                                      text=error_msg)
        else:
            Bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text="Threshold votes not reached before poll expiry.")
