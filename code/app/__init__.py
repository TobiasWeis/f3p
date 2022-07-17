from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from flask_apscheduler import APScheduler
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.schedulers import SchedulerAlreadyRunningError
import atexit

from .db_extensions import db
from .FFScraper import FFScraper
from .utils import *

scheduler = APScheduler()

def create_app():
    from . import models
    from .views.pages import pages_blueprint

    app = Flask(__name__, instance_relative_config=False)

    app.config.from_object('config.Config')

    CORS(app)

    db.init_app(app)

    app.register_blueprint(pages_blueprint)


    with app.app_context():
        db.create_all()
        seed_data(db, models)

        Swagger(app)

        clubs = ['wiesbaden1', 'frankfurt8', 'berlin2', 'hamburg1']

        scrapers = []
        for c in clubs:
            fs = FFScraper(c, app)
            scrapers.append(fs)
            try:
                # get the current checkins every minute
                scheduler.add_job(id=f"checkins for {c}",
                                  func=fs.get_checkins,
                                  trigger='cron',
                                  minute='*/1',
                                  hour='*')
                # get the courses of the club only every 30 mins
                scheduler.add_job(id=f"courses for {c}",
                                  func=fs.get_courses,
                                  trigger='cron',
                                  minute='*/30',
                                  hour='*')

            except ConflictingIdError:
                print("ERROR: Schedule job was already there")
                pass

        try:
            scheduler.init_app(app)
            scheduler.start()
            atexit.register(lambda:scheduler.shutdown())
        except SchedulerAlreadyRunningError:
            print("ERROR: Scheduler already running")

        return app
