from flask import Blueprint, jsonify, request
from flask import render_template
import datetime
import pandas as pd
import numpy as np

from sqlalchemy import and_

from app import db, cache
from app.models import Timepoint, Club, Course, TimepointWeather

pages_blueprint = Blueprint('pages_blueprint', __name__, url_prefix="", template_folder='../templates/', static_folder='static', static_url_path='../static/')

@pages_blueprint.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@pages_blueprint.route('/detail', methods=['GET'])
def detail_page():
    return render_template('detail.html')

@pages_blueprint.route('/analysis', methods=['GET'])
def analysis_page():
    return render_template('analysis.html')

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

    timepoints = Timepoint.query.filter(Timepoint.id_club==club.id).order_by(Timepoint.timestamp.desc()).limit(1440*7).all()
    for tp in timepoints:
        ret['timepoints'].append([tp.timestamp, tp.checkins, tp.total_allowed])

    timepoints_weather = TimepointWeather.query.filter(
            and_(
                TimepointWeather.id_club == club.id,
                TimepointWeather.timestamp >= timepoints[-1].timestamp
            )).order_by(TimepointWeather.timestamp.desc()).all()
    for tpw in timepoints_weather:
        ret['timepoints_weather'].append([tpw.timestamp, tpw.temperature])

    courses = Course.query.filter(Course.id_club==club.id).filter(
            and_(
                Course.time_start >= timepoints[-1].timestamp,
                Course.time_start < timepoints[0].timestamp
                )).all()
    for c in courses:
        ret['courses'].append([c.is_cancelled, c.title, c.time_start, c.time_end])

    return jsonify(ret)

def get_minute_of_day(time):
    minutes = 0
    minutes += time.hour*60
    minutes += time.minute
    return minutes

def make_cache_key(*args, **kwargs):
    path = request.path
    key_vals = str(hash(frozenset(request.json.items())))
    cache_key = (path + key_vals).encode('utf-8')
    print("Cache key is:",cache_key)
    return cache_key

@pages_blueprint.route('/api/analysis', methods=['POST'])
@cache.cached(timeout=60*60*24*7, key_prefix=make_cache_key)
def analysis():
    data = request.json
    club = Club.query.filter(Club.name == data['club_name']).first()

    timepoints = Timepoint.query.filter(Timepoint.id_club == club.id).order_by(Timepoint.timestamp).all()

    df = pd.DataFrame(
            [(tp.checkins, tp.total_allowed, tp.timestamp) for tp in timepoints], 
            columns=['checkins', 'total_allowed', 'timestamp'])  

    df['percentage'] = df['checkins'] / df['total_allowed'] * 100.
    df['datetime'] = pd.to_datetime(df.timestamp * 1e9)
    df['weekday'] = df['datetime'].dt.dayofweek
    df['minute_of_day'] = df.apply(lambda x: get_minute_of_day(x['datetime'].time()), axis=1)

    # divide into chunks of days
    results = [group[1] for group in df.groupby(df.datetime.dt.date)]

    # we should have 24*60=1440 results if the complete day was captured
    # we NEVER got the full 1440 datapoints?!
    # lets use a bit less
    full_results = []
    for r in results:
        if len(r) >= 1300:
            full_results.append(r)
    print(f"Got {len(full_results)} \"full\" days")

    # interpolate missing values to have full 1440-item-arrays
    new_full_results = []
    for fr in full_results:
        all_minutes_of_day = list(range(1441))
        minutes_in_dataframe = list(fr.minute_of_day)

        missing_minutes = []
        for amod in all_minutes_of_day:
            if amod not in minutes_in_dataframe:
                missing_minutes.append(amod)

        # interpolate missing minutes
        for mm in missing_minutes:
            #print(f"Computing minute {mm}")
            if mm > 0:
                value_before = fr[fr.minute_of_day == mm-1].percentage.iloc[0]

            if mm < 1440:
                for i in range(1,1440-mm):
                    if not fr[fr.minute_of_day == mm+i].empty:
                        #print(f"--> using value of {(mm+i)}")
                        value_after = fr[fr.minute_of_day == mm+i].percentage.iloc[0]
                        break
            else:
                value_after = value_before

            if mm == 0:
                value_bevore = value_after

            #print(f"\tValue before: {value_before}, value after: {value_after}")
            interp_value = (value_after + value_before)/2

            my_new_row = fr.iloc[0]
            my_new_row.minute_of_day = mm
            my_new_row.percentage = interp_value
            my_new_row.id = None

            fr = pd.concat([fr, pd.DataFrame([my_new_row])], ignore_index=True)

        fr.sort_values(by='minute_of_day', inplace=True)
        new_full_results.append(fr)
        print(f"Missing minutes of day: {missing_minutes}")

    full_results = new_full_results

    weekday_arrays = {}
    for r in full_results:
        dayname = r.iloc[0].datetime.day_name()
        if dayname not in weekday_arrays.keys():
            weekday_arrays[dayname] = []

        weekday_arrays[dayname].append(np.array([r.minute_of_day, r.percentage]))
    
    weekday_means = {}
    for day_name, arrays in weekday_arrays.items():
        dayarrays = np.array(arrays)
        weekday_means[day_name] = list(np.mean(dayarrays[:,1], axis=0))

    #ret = {'data': weekday_arrays}
    return jsonify(weekday_means)

