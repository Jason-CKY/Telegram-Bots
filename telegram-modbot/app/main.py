from typing import Optional
import os, json, requests
from fastapi import FastAPI, Request
from telegram import Bot
from telegram.ext import ExtBot

app = FastAPI()
bot = ExtBot(token=os.getenv('BOT_TOKEN'))

def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def process_command(data, command):
    if command == '/start':
        bot.send_message(data['message']['chat']['id'], START_MESSAGE)
    
@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/modbot")
def ngrok_url():
    return {
        "Ngrok url": os.getenv('PUBLIC_URL')
        }

@app.post(f"/modbot/{os.getenv('BOT_TOKEN')}")
async def respond(request:Request):
    req = await request.body()
    req = json.loads(req)
    write_json(req, "/code/app/output.json")
    return {
        "Ngrok url": os.getenv('PUBLIC_URL')
        }
