from . import db
from sqlalchemy import event
import uuid
import datetime
from flask import current_app


def create_log_message(startstring, target):
    """
    Creates log-messages that contain the table/object-name and it's attributes and values
    """
    string = f"{startstring} {target.__class__.__name__}: "
    for k, v in target.__dict__.items():
        if k not in ["password", "id", "_sa_instance_state"]:
            string += f"{k}:{v}, "

    current_app.logger.debug(string)

    return string


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)

    def getZipcode(self):
        # Luxemburger Str. 253, 50939 Köln
        return self.address.split(",")[-1].split(" ")[1]


    def __repr__(self):
        return f"""<Club id:{id}, name:{name}>"""


class Timepoint(db.Model):
    __tablename__ = 'timepoint'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_club = db.Column(db.String, db.ForeignKey('club.id'), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False, default=datetime.datetime.utcnow)
    checkins = db.Column(db.Integer, nullable=False)
    total_allowed = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"""<Timepoint: {self.timestamp}, {self.checkins}/{self.total_allowed}>"""


class TimepointWeather(db.Model):
    __tablename__ = 'timepoint_weather'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_club = db.Column(db.String, db.ForeignKey('club.id'), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False, default=datetime.datetime.utcnow)
    temperature = db.Column(db.Float, nullable=False)



class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_club = db.Column(db.String, db.ForeignKey('club.id'), nullable=False)
    is_cancelled = db.Column(db.Boolean)
    is_changed = db.Column(db.Boolean)
    level = db.Column(db.String)
    title = db.Column(db.String)
    time_start = db.Column(db.Integer)
    time_end = db.Column(db.Integer)

