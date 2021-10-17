import json, logging
import pymongo
from fastapi import FastAPI, Depends
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from app.database import get_client
from apscheduler.jobstores.mongodb import MongoDBJobStore

def alarm(time: datetime) -> None:
    print('Alarm! This alarm was scheduled at %s.' % time)

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = FastAPI()
scheduler = BackgroundScheduler(timezone=utc)
scheduler.add_jobstore(MongoDBJobStore(client=get_client()))    

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


def write_json(data, fname):
    with open(fname, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.get("/")
def root():
    alarm_time = datetime.now() + timedelta(seconds=120)
    scheduler.add_job(alarm, 'date', run_date=alarm_time, args=[datetime.now()])
    return {
        "Hello": "World",
        "scheduler.get_jobs()": [str(job) for job in scheduler.get_jobs()]
    }

