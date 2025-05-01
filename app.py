from flask import Flask, jsonify, request
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os
import json

from GolfCourse import GolfCourse

app = Flask(__name__)

with open('./golf_courses.json', 'r') as f:
  courses_data = json.load(f)

courses = [GolfCourse(**course) for course in courses_data]

@app.route('/tee_times', methods=['GET'])
def get_tee_times():
  date = request.args.get('date', default=datetime.today().strftime('%Y-%m-%d'))
  players = int(request.args.get('players', 4))

  tee_times_df = pd.DataFrame()

  for course in courses:
    if course.source == 'bookateetime':
      # Make a GET request to the URL with the course name and date
      response = requests.get(f"https://bookateetime.teequest.com/search/{course.id}/{date}?selectedPlayers={players}&selectedHoles=18")

      # Decode the response content as a string
      content_str = response.content.decode('utf-8')
      soup = BeautifulSoup(content_str, 'html.parser')
      tee_times = []

      for tee_time_div in soup.find_all('div', class_='tee-time'):
        href = tee_time_div.find('a', class_='btn')['href']
        tt = {
          'course': course.name,
          'tee_time': pd.to_datetime(tee_time_div['data-date-time'], format='%Y%m%d%H%M'), #tee_time_div['data-date-time'],
          'price': float(tee_time_div['data-price']),
          'players': int(tee_time_div['data-available']),
          'lat': course.lat,
          'lon': course.lon,
          'book_url': f'https://bookateetime.teequest.com{href}'
        }
        tee_times.append(tt)

      tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

    if course.source == 'golfback':
      url = f"https://api.golfback.com/api/v1/courses/{course.id}/date/{date}/teetimes"
      headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://golfback.com/",
        "Content-Type": "application/json",
      }
      params = {
        "date": date,
        "course_id": course.id,
        "players": players
      }

      response = requests.post(url, headers=headers, json=params)
      tee_times_raw = response.json()['data']
      
      tee_times = []
      for tee_time in tee_times_raw:
        tt = {
          'course': course.name,
          'tee_time': pd.to_datetime(tee_time['dateTime'], format='%Y-%m-%dT%H:%M:%S%z') \
            .astimezone(pytz.timezone("US/Central")).strftime("%Y-%m-%d %H:%M:%S"),
          'price': float(tee_time['rates'][0]['price']),
          'players': tee_time['playersMax'],
          'lat': course.lat,
          'lon': course.lon,
          'book_url': f'https://golfback.com/#/course/{course.id}/date/{date}/teetime/{tee_time['id']}?rateId={tee_time['rates'][0]['ratePlanId']}&holes=18&players={players}'
        }
        tee_times.append(tt)

      tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)
    
    if course.source == 'foreup':
      flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
      url = f"https://foreupsoftware.com/index.php/api/booking/times?time=all&date={flip_date}&holes=all&players={players}&booking_class=14824&schedule_id={course.id}&api_key=no_limits"
      headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://foreupsoftware.com/index.php/booking/22857/7340",
        "Content-Type": "application/json",
      }
      params = {
        "date": datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y'),
        "players": players,
      }

      response = requests.get(url, headers=headers, json=params)
      tee_times_raw = response.json()

      tee_times = []
      for tee_time in tee_times_raw:
        # print(tee_time)
        # break
        tt = {
          'course': course.name,
          'tee_time': pd.to_datetime(tee_time['time'], format='%Y-%m-%d %H:%M'),
          'price': float(tee_time['green_fee'] + tee_time['cart_fee']),
          'players': tee_time['available_spots'],
          'lat': course.lat,
          'lon': course.lon,
          'book_url': f'https://foreupsoftware.com/index.php/booking/22857/{course.id}#/teetimes'
        }
        tee_times.append(tt)

      tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

  return jsonify(tee_times_df.to_dict(orient='records'))


if __name__ == '__main__':
  # app.run(debug=True)
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port, debug=True)