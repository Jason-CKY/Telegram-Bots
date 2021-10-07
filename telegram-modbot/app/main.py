from typing import Optional
import os, json, requests
from app.credentials import *
from fastapi import FastAPI, Request, Response, status
from telegram import Bot
from telegram.ext import ExtBot

app = FastAPI()
Bot = ExtBot(token=BOT_TOKEN)

def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def process_command(data, command):
    if command == '/start':
        Bot.send_message(data['message']['chat']['id'], START_MESSAGE)
    
@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/modbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL
        }

@app.post(f"/modbot/{BOT_TOKEN}")
async def respond(request:Request):
    req = await request.body()
    update = json.loads(req)
    write_json(update, "/code/app/output.json")
    if 'message' in update and 'text' in update['message']: # if its a text message
        print("processing a message")
        text = update['message']['text']
        if update['message']['chat']['type'] == 'private':
            if text == '/start':
                msg = START_MESSAGE
            else:
                msg = "Commands only work on group chats."
            Bot.send_message(update['message']['chat']['id'], msg)
    return Response(status_code=status.HTTP_200_OK)