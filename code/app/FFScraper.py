import time
import datetime
import json
import requests

from flask import current_app
from sqlalchemy import and_

from app import db
from app.models import Club, Timepoint, Course, TimepointWeather


class FFScraper:
    def __init__(self, club_name, app):
        self.club_name = club_name
        self.app = app

        self.club = Club.query.filter(Club.name == club_name).first()
        self.club_id = self.club.id
        assert(self.club_id is not None)

    def get_api_url_checkins(self):
        return f"https://www.fitnessfirst.de/club/api/checkins/{self.club_name}"

    def get_api_url_courses(self):
        return "https://www.fitnessfirst.de/kurse/kursplan/search?club_id=%04d&category_id=&class_id=&daytime_id=" % (self.club_id)

    def get_api_url_weathermap(self):
        zipcode = self.club.getZipcode()
        apikey = current_app.config['OPENWEATHERMAP_API_KEY']
        url = f"https://api.openweathermap.org/data/2.5/weather?zip={zipcode},DE&units=metric&appid={apikey}"
        return url

    def get_weather_for_zipcode(self):
        with self.app.app_context():
            response = requests.get(self.get_api_url_weathermap())
            if response.status_code == 200:
                res = json.loads(response.content.decode('utf-8'))
                temp = res['main']['temp']
                print(f"{self.club.address}: {temp}")
                tpw = TimepointWeather(
                            id_club=self.club_id,
                            timestamp=time.time(),
                            temperature=float(temp)
                        )
                db.session.add(tpw)
                db.session.commit()
            else:
                print(f"[{self.club_name}] Weather error")
                print(response)

    def get_checkins(self):
        with self.app.app_context():
            #print(f"[{self.club_name}] Getting timepoint")
            response = requests.get(self.get_api_url_checkins())
            if response.status_code == 200:
                res = json.loads(response.content.decode('utf-8'))
                tp = Timepoint(
                        id_club=self.club_id,
                        timestamp=time.time(),
                        checkins=res['data']['check_ins'],
                        total_allowed=res['data']['allowed_people']
                        )
                db.session.add(tp)
                db.session.commit()
            else:
                print(f"[{self.club_name}] Timepoint error")


    def get_courses(self):
        with self.app.app_context():
            response = requests.get(self.get_api_url_courses())
            if response.status_code == 200:
                data = json.loads(response.content.decode('utf-8'))['data']
                for c in data['classes']:
                    date_str = c.split("_")[0]

                    for timesel in ["before_noon", "afternoon","evening"]:
                        try:
                            courses = data['classes'][c][timesel]

                            for course in courses:
                                title = course["title"]
                                timestart_str = f"{date_str} {course['time']['from']}"
                                timeend_str = f"{date_str} {course['time']['to']}"
                                #print(f"{timestart_str}-{timeend_str}: {title}")

                                ts_start = time.mktime(datetime.datetime.strptime(timestart_str, "%Y-%m-%d %H:%M").timetuple())
                                ts_end = time.mktime(datetime.datetime.strptime(timeend_str, "%Y-%m-%d %H:%M").timetuple())

                                thiscourse = db.session.query(Course).filter(and_(Course.title == title, Course.time_start == ts_start, Course.id_club == self.club_id)).first()
                                if thiscourse is None: # add course to db
                                    db.session.add(Course(
                                        id_club=self.club_id,
                                        is_cancelled=course["is_cancelled"],
                                        is_changed=course["is_changed"],
                                        level=course["level"],
                                        title=course["title"],
                                        time_start=ts_start,
                                        time_end=ts_end
                                        ))
                                else: # just update
                                    thiscourse.is_cancelled = course["is_cancelled"]
                                    thiscourse.is_changed = course["is_changed"]
                                db.session.commit()

                        except Exception as e:
                            print("oops: ")
                            print(e)
            else:
                print(f"[{self.club_name}] Error Courses:")
                print(response)
                
