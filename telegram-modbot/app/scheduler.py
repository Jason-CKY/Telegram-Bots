from pytz import utc
from app.database import get_client
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

jobstores = {
    'mongo': MongoDBJobStore(client=get_client())
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': False,      # whether to only run the job once when several run times are due
    'max_instances': 3      # the maximum number of concurrently executing instances allowed for this job
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)