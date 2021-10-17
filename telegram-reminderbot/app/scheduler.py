"""
This example demonstrates the use of the MongoDB job store.
On each run, it adds a new alarm that fires after ten seconds.
You can exit the program, restart it and observe that any previous alarms that have not fired yet
are still active. Running the example with the --clear switch will remove any existing alarms.
"""

from datetime import datetime, timedelta
import sys
import os, time
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from database import get_client
from apscheduler.jobstores.mongodb import MongoDBJobStore
import logging

def alarm(time):
    print('Alarm! This alarm was scheduled at %s.' % time)


if __name__ == '__main__':
    # logging.basicConfig()
    # logging.getLogger('apscheduler').setLevel(logging.DEBUG)
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.add_jobstore(MongoDBJobStore(client=get_client()))
    client = get_client()
    print(list(client['apscheduler']['jobs'].find()))
    # print(scheduler.get_jobs())
    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        scheduler.remove_all_jobs()

    alarm_time = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(alarm, 'date', run_date=alarm_time, args=[datetime.now()])
    # print(scheduler.get_jobs())
    scheduler.start()
    print('To clear the alarms, run this example with the --clear argument.')
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        pass