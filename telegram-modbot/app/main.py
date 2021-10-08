import os, json, requests
from app.database import engine, get_db, Base
from typing import Optional
from app import utils, commands
from app.constants import *
from fastapi import FastAPI, Request, Response, status
from munch import Munch


app = FastAPI()

def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def process_command(update:Munch):
    command = utils.extract_command(update)
    return COMMANDS[command](update)

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

@app.post(f"/modbot/{BOT_TOKEN}")
async def respond(request:Request):
    try:
        req = await request.body()
        update = json.loads(req)
        update = Munch.fromDict(update)
        write_json(update, "/code/app/output.json")
        if utils.is_text_message(update):
            print("processing a message")
            if utils.is_private_message(update):
                process_private_message(update)
            elif utils.is_group_message(update) and utils.is_valid_command(update):
                # TODO: write script for all commands
                process_command(update)
        elif utils.added_to_group(update):
            # TODO: add default config into db and 
            # add message for added to group event
            Bot.send_message(update.message.chat.id, "Added to group!")
        elif utils.removed_from_group(update):
            # TODO: remove config data from group that was kicked from
            Bot.send_message(DEV_CHAT_ID, f"left group {update.message.chat.title}, id={update.message.chat.id}")
        elif utils.poll_updates(update):
            # TODO: update poll results in db and check for poll finish criteria
            Bot.send_message(DEV_CHAT_ID, "someone updated a poll!")
    except Exception as e:
        print(e)
        return Response(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)    
            
    return Response(status_code=status.HTTP_200_OK)