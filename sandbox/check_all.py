# %%
from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
from datetime import datetime

# %%
sw_lat, sw_long = 38.857489, -94.846741
ne_lat, ne_long = 39.297268, -94.325766
query = f"""
[out:json];
(
  node["leisure"="golf_course"]({sw_lat}, {sw_long}, {ne_lat}, {ne_long});
  way["leisure"="golf_course"]({sw_lat}, {sw_long}, {ne_lat}, {ne_long});
  relation["leisure"="golf_course"]({sw_lat}, {sw_long}, {ne_lat}, {ne_long});
);
out center;
"""

response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
data = response.json()
for el in data["elements"]:
  name = el.get("tags", {}).get("name")
  if name != None:
    print(name)

# %%
# Course Data
bookateetime_courses = {
  'Shoal Creek': '118-1',
  'Hodge Park': '117-1',
  'WinterStone': '62-1',
  'Adams Pointe': '45-1',
  'Heart of America': '49-1',
  'Sycamore Ridge': '44-1',
  'Paradise Pointe - The Outlaw': '24-1',
  'Paradise Pointe - The Posse': '24-2',
}

chronogolf_courses = {
  'Falcon Lakes': 6633,
}

golfback_courses = {
  'Dubs Dread': '398d44ce-a908-4ce7-8f50-e5f4bdc77b73',
  'Painted Hills': '857a12d4-a9cf-4a43-afe2-60940bdc7438',
  'Drumm Farm - Full': 'd70999c9-d7d4-4008-9f41-4e9551b3c796',
  'Drumm Farm - Executive': '9a1de435-8a46-4840-9cdc-332c3cfea782',
  'Royal Meadows': 'd2278228-4700-4354-95a8-422a8f9a5a16'
}

foreup_courses = {
  'Teetering Rocks': 7341,
  'Heritage Park': 12159,
  'Tomahawk Hills': 11026,
}

loners = {
  'Sunflower Hills': 'https://www.sunflowerhillsgolfcourse.com/TeeTimes',
}

# %%
date = '2025-04-26'
players = 4

tee_times_df = pd.DataFrame()

for course in bookateetime_courses.items():
  # Make a GET request to the URL with the course name and date
  response = requests.get(f"https://bookateetime.teequest.com/search/{course[1]}/{date}?selectedPlayers={players}&selectedHoles=18")

  # Decode the response content as a string
  content_str = response.content.decode('utf-8')
  soup = BeautifulSoup(content_str, 'html.parser')
  tee_times = []

  for tee_time_div in soup.find_all('div', class_='tee-time'):
    tt = {
      'course': course[0],
      'tee_time': tee_time_div['data-date-time'],
      'price': float(tee_time_div['data-price']),
      'players': int(tee_time_div['data-available']),
    }
    tee_times.append(tt)

  tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)

# Convert the 'date_time' column to datetime format
tee_times_df['tee_time'] = pd.to_datetime(tee_times_df['tee_time'], format='%Y%m%d%H%M')

# %%
for course in golfback_courses.items():
  url = f"https://api.golfback.com/api/v1/courses/{course[1]}/date/{date}/teetimes"
  headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://golfback.com/",
    "Content-Type": "application/json",
  }
  params = {
    "date": date,
    "course_id": course[1],
    "players": players
  }

  response = requests.post(url, headers=headers, json=params)
  tee_times_raw = response.json()['data']

  tee_times = []
  for tee_time in tee_times_raw:
    tt = {
      'course': course[0],
      'tee_time': pd.to_datetime(tee_time['dateTime'], format='%Y-%m-%dT%H:%M:%S%z').tz_localize(None),
      'price': float(tee_time['rates'][0]['price']),
      'players': tee_time['playersMax']
    }
    tee_times.append(tt)

  tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)


# %%
tee_times_df

# %%
for course in foreup_courses.items():
  flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
  url = f"https://foreupsoftware.com/index.php/api/booking/times?time=all&date={flip_date}&holes=all&players={players}&booking_class=14824&schedule_id={course[1]}&api_key=no_limits"
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
    tt = {
      'course': course[0],
      'tee_time': pd.to_datetime(tee_time['time'], format='%Y-%m-%d %H:%M'),
      'price': float(tee_time['green_fee'] + tee_time['cart_fee']),
      'players': tee_time['available_spots']
    }
    tee_times.append(tt)

  tee_times_df = pd.concat([tee_times_df, pd.DataFrame(tee_times)], ignore_index=True)


# %%
tee_times_df['tee_time'] = pd.to_datetime(tee_times_df['tee_time'], utc=True)

# %%
tee_times_df

# %%
tee_times_df.course.value_counts()

# %%
tee_times_df[
  (tee_times_df['tee_time'].dt.hour >= 9) &
  (tee_times_df['tee_time'].dt.hour < 15) &
  (tee_times_df['price'] <= 90) &
  (tee_times_df['price'] >= 25)
].sort_values(by=['course', 'tee_time']).to_csv('tee_times.csv', index=False)

# %%
tee_times_df[
  (tee_times_df['tee_time'].dt.hour >= 16) &
  (tee_times_df['price'] >= 25) &
  (tee_times_df['players'] == 4)
].to_csv('tee_times.csv', index=False)

# %%



