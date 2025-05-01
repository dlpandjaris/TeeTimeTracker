from flask import Flask, jsonify, request
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# Course Data
bookateetime_courses = {
  'Shoal Creek Golf Course': '118-1',
  'Hodge Park Golf Course': '117-1',
  'Winterstone Golf Course': '62-1',
  'Adams Pointe Golf Course': '45-1',
  'Heart of America Golf Course': '49-1',
  'Sycamore Ridge Golf Club': '44-1',
  'Paradise Pointe Golf Course - The Outlaw': '24-1',
  'Paradise Pointe Golf Course - The Posse': '24-2',
}

golfback_courses = {
  "Dub's Dread Golf Club": '398d44ce-a908-4ce7-8f50-e5f4bdc77b73',
  'Painted Hills Golf Club': '857a12d4-a9cf-4a43-afe2-60940bdc7438',
  'Drumm Farm Golf Club - Full': 'd70999c9-d7d4-4008-9f41-4e9551b3c796',
  'Drumm Farm Golf Club - Executive': '9a1de435-8a46-4840-9cdc-332c3cfea782',
  'Royal Meadows Golf Club': 'd2278228-4700-4354-95a8-422a8f9a5a16'
}

foreup_courses = {
  'Teetering Rocks Golf Course': 7341,
  'Heritage Park Golf Course': 12159,
  'Tomahawk Hills Golf Course': 11026,
}


@app.route('/tee_times', methods=['GET'])
def get_tee_times():
  date = request.args.get('date', default=datetime.today().strftime('%Y-%m-%d'))
  players = int(request.args.get('players', 4))

  tee_times_df = pd.DataFrame()

  # BookATeeTime scraping
  for course_name, course_id in bookateetime_courses.items():
    response = requests.get(f"https://bookateetime.teequest.com/search/{course_id}/{date}?selectedPlayers={players}&selectedHoles=18")
    soup = BeautifulSoup(response.content, 'html.parser')
    tee_times = [
      {
        'course': course_name,
        'tee_time': div['data-date-time'],
        'price': float(div['data-price']),
        'players': int(div['data-available']),
      }
      for div in soup.find_all('div', class_='tee-time')
    ]
    tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

  # GolfBack API
  for course_name, course_id in golfback_courses.items():
    url = f"https://api.golfback.com/api/v1/courses/{course_id}/date/{date}/teetimes"
    headers = {
      "User-Agent": "Mozilla/5.0",
      "Referer": "https://golfback.com/",
      "Content-Type": "application/json",
    }
    params = {"date": date, "course_id": course_id, "players": players}
    response = requests.post(url, headers=headers, json=params)
    tee_times_raw = response.json().get('data', [])
    tee_times = [
      {
        'course': course_name,
        'tee_time': pd.to_datetime(tt['dateTime'], format='%Y-%m-%dT%H:%M:%S%z') \
          .astimezone(pytz.timezone("US/Central")).strftime("%Y-%m-%d %H:%M:%S"),
        'price': float(tt['rates'][0]['price']),
        'players': tt['playersMax']
      }
      for tt in tee_times_raw
    ]
    tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

  # ForeUp API
  for course_name, schedule_id in foreup_courses.items():
    flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
    url = f"https://foreupsoftware.com/index.php/api/booking/times?time=all&date={flip_date}&holes=all&players={players}&booking_class=14824&schedule_id={schedule_id}&api_key=no_limits"
    headers = {
      "User-Agent": "Mozilla/5.0",
      "Referer": f"https://foreupsoftware.com/index.php/booking/22857/7340",
      "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    tee_times_raw = response.json()
    tee_times = [
      {
        'course': course_name,
        'tee_time': pd.to_datetime(tt['time'], format='%Y-%m-%d %H:%M'),
        'price': float(tt['green_fee'] + tt['cart_fee']),
        'players': tt['available_spots']
      }
      for tt in tee_times_raw
    ]
    tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

  # tee_times_df['tee_time'] = pd.to_datetime(tee_times_df['tee_time'], utc=True)

  return jsonify(tee_times_df.to_dict(orient='records'))


if __name__ == '__main__':
  # app.run(debug=True)
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port, debug=True)