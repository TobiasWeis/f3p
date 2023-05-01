from flask import Blueprint, jsonify, request
from flask import render_template
import datetime

from sqlalchemy import and_

from app import db
from app.models import Timepoint, Club, Course, TimepointWeather

pages_blueprint = Blueprint('pages_blueprint', __name__, url_prefix="", template_folder='../templates/', static_folder='static', static_url_path='../static/')

@pages_blueprint.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@pages_blueprint.route('/detail', methods=['GET'])
def detail_page():
    return render_template('detail.html')

@pages_blueprint.route('/api/clubs', methods=['POST'])
def clubs():
    clubs = Club.query.order_by(Club.title).all()
    ret = []
    for c in clubs:
        ret.append({'title':c.title, 'name':c.name})
    return jsonify(ret)

@pages_blueprint.route('/api/status', methods=['POST'])
def status():
    clubs = Club.query.order_by(Club.title).all()

    data = []

    for club in clubs:
        lt = Timepoint.query.filter(Timepoint.id_club == club.id).order_by(Timepoint.timestamp.desc()).limit(1).first()
        if lt is not None:
            #print("club:",club.name,",checkins:",lt.checkins,",total-allowed:",lt.total_allowed)
            thisdata = {
                    'name':club.title, 
                    'perc':int((lt.checkins/float(lt.total_allowed))*100.),
                    'datestr':datetime.datetime.fromtimestamp(lt.timestamp)}
            data.append(thisdata)

    return jsonify(data)

@pages_blueprint.route('/api/detail', methods=['POST'])
def detail():
    data = request.json
    club = Club.query.filter(Club.name == data['club_name']).first()

    ret = {}
    ret['timepoints'] = []
    ret['timepoints_weather'] = []
    ret['courses'] = []

    timepoints = Timepoint.query.filter(Timepoint.id_club==club.id).order_by(Timepoint.timestamp).limit(1440*7).all()
    for tp in timepoints:
        ret['timepoints'].append([tp.timestamp, tp.checkins, tp.total_allowed])

    timepoints_weather = TimepointWeather.query.filter(TimepointWeather.id_club==club.id).order_by(TimepointWeather.timestamp).all()
    for tpw in timepoints_weather:
        ret['timepoints_weather'].append([tpw.timestamp, tpw.temperature])

    courses = Course.query.filter(Course.id_club==club.id).filter(
            and_(
                Course.time_start >= timepoints[0].timestamp,
                Course.time_start < timepoints[-1].timestamp
                )).all()
    for c in courses:
        ret['courses'].append([c.is_cancelled, c.title, c.time_start, c.time_end])

    return jsonify(ret)
