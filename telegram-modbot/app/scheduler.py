from pytz import utc
from app import database, utils
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_MISSED

# jobstores = {
#     'mongo': MongoDBJobStore(client=get_client())
# }
# executors = {
#     'default': ThreadPoolExecutor(20)
# }
# job_defaults = {
#     'coalesce': False,      # whether to only run the job once when several run times are due
#     'max_instances': 3      # the maximum number of concurrently executing instances allowed for this job
# }
# scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)

def listener(event):
    client = database.get_client()
    db = client[database.MONGO_DB]
    poll_id = database.get_poll_id_from_job_id(event.job_id, db)
    utils.settle_poll(poll_id)
    client.close()
    
scheduler = BackgroundScheduler(timezone=utc)
scheduler.add_jobstore(MongoDBJobStore(client=database.get_client()))    
scheduler.add_listener(listener, EVENT_JOB_MISSED)