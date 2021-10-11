import json, pymongo, time
from app import utils, commands, database
from app.database import get_db
from app.constants import *
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch
from telegram.error import BadRequest

app = FastAPI()

def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def process_command(update:Munch, db: pymongo.database.Database):
    command = utils.extract_command(update)
    return COMMANDS[command](update, db)

def process_private_message(update:Munch):
    text = update.message.text
    if text == '/start':
        commands.start(update)
    else:
        msg = "Commands only work on group chats."
        Bot.send_message(update.message.chat.id, msg)

@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/modbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict()
        }

@app.get("/modbot/insert")
def ngrok_url(db: pymongo.database.Database = Depends(get_db)):
    # create collection
    mycol = db['test-collection']
    mydict = { "name": "John", "address": "Highway 37" , "timestamp": time.time()}
    x = mycol.insert_one(mydict)
    output = list(mycol.find({}, {'_id': 0}))
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "db output": output
        }

@app.post(f"/modbot/{BOT_TOKEN}")
async def respond(request:Request, db: pymongo.database.Database = Depends(get_db)):
    req = await request.body()
    update = json.loads(req)
    update = Munch.fromDict(update)
    write_json(update, "/code/app/output.json")
    # TODO 1: finish this part and test it
    # TODO 2: find a way to schedule tasks
    # if utils.superchat_created(update): 
        
    if utils.is_text_message(update):
        print("processing a message")
        if utils.is_private_message(update):
            process_private_message(update)
        elif utils.is_group_message(update) and utils.is_valid_command(update):
            # TODO: write script for /delete
            print("processing command")
            process_command(update, db)
    elif utils.added_to_group(update):
        database.add_chat_collection(update, db)
        # send message stating the default calculated threshold and how to change it for administrators
        num_members = Bot.get_chat_member_count(update.message.chat.id)
        bot_username = Bot.get_me().username
        chat_config = {
            "expiryTime": POLL_EXPIRY,
            "threshold": int(num_members/2)
        }
        database.update_chat_configs(update, db, chat_config)

        msg = f"{START_MESSAGE}\n\nThe default threshold is half the number of members in this group ({chat_config['threshold']}), " +\
            f"and default expiration time is {chat_config['expiryTime']} seconds before poll times out.\n" +\
            f"Set your own threshold by typing '/setthreshold@{bot_username} <number>'\n " +\
                f"Set your own threshold by typing '/setexpiry@{bot_username} <number>'"

        Bot.send_message(update.message.chat.id, msg)

    elif utils.removed_from_group(update):
        database.delete_chat_collection(update.my_chat_member.chat.id, db)
        Bot.send_message(DEV_CHAT_ID, f"left group {update.my_chat_member.chat.title}, id={update.my_chat_member.chat.id}")

    elif utils.poll_updates(update):
        chat_id = database.get_chat_id_from_poll_id(update.poll.id, db)
        poll_message_id = database.get_message_id_from_poll_id(update.poll.id, db)
        message_id = database.get_message_id_from_poll_id(update.poll.id, db)
        _, threshold = database.get_config(chat_id, db)
        delete_count = [d for d in update.poll.options if d.get('text') == 'Delete'][0].get('voter_count')
        if delete_count >= threshold:
            try:
                Bot.delete_message(chat_id, message_id)
                Bot.stop_poll(chat_id, poll_message_id)
                Bot.send_message(chat_id, "Offending message has been deleted.")
            except BadRequest as e:
                Bot.send_message(chat_id, e.message)
            
    return Response(status_code=status.HTTP_200_OK)