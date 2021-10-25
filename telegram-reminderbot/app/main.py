import json, pymongo, logging
from app import utils, commands, database
from app.scheduler import scheduler
from app.database import get_db
from app.constants import *
from fastapi import FastAPI, Request, Response, status, Depends
from munch import Munch

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

def process_command(update:Munch, db: pymongo.database.Database):
    command = utils.extract_command(update)
    return COMMANDS[command](update, db)

@app.get("/")
def root():
    return {
        "Hello": "World"
    }

@app.get("/reminderbot")
def ngrok_url():
    return {
        "Ngrok url": PUBLIC_URL,
        "Bot Info": Bot.get_me().to_dict(),
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
        }

@app.post(f"/reminderbot/{BOT_TOKEN}")
async def respond(request:Request, db: pymongo.database.Database = Depends(get_db)):
    try:
        req = await request.body()
        update = Munch.fromDict(json.loads(req))
        utils.write_json(update, f"/code/app/output.json")

        # TODO: modify this function at the last
        # if utils.group_upgraded_to_supergroup(update): 
        #     mapping = utils.get_migrated_chat_mapping(update)
        #     database.update_chat_id(mapping, db)

        if utils.is_valid_command(update):
            process_command(update, db)
        elif utils.is_text_message(update): # this will be a normal text message if pm, and any text messages that is a reply to bot in group due to bot privacy setting
            pass
        
    except Exception as e:
        Bot.send_message(DEV_CHAT_ID, getattr(e, 'message', str(e)))
            
    return Response(status_code=status.HTTP_200_OK)