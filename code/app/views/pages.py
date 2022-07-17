from flask import Blueprint, jsonify
from flask import render_template
import datetime

from app import db
from app.models import Timepoint, Club

pages_blueprint = Blueprint('pages_blueprint', __name__, url_prefix="", template_folder='../templates/', static_folder='static', static_url_path='../static/')

@pages_blueprint.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@pages_blueprint.route('/status', methods=['POST'])
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
