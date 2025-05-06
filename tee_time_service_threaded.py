from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import json

from GolfCourse import GolfCourse


with open('./golf_courses.json', 'r') as f:
  courses_data = json.load(f)

courses = [GolfCourse(**course) for course in courses_data]


# --- BookATeeTime ---
def fetch_bookateetime(course, date, players):
  try:
    url = f"https://bookateetime.teequest.com/search/{course.id}/{date}?selectedPlayers={players}&selectedHoles=18"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    tee_times = []

    for tee_time_div in soup.find_all('div', class_='tee-time'):
      href = tee_time_div.find('a', class_='btn')['href']
      tee_times.append({
        'course': course.name,
        'tee_time': pd.to_datetime(tee_time_div['data-date-time'], format='%Y%m%d%H%M')
                      .tz_localize('US/Central').tz_convert('UTC'),
        'price': float(tee_time_div['data-price']),
        'players': int(tee_time_div['data-available']),
        'lat': course.lat,
        'lon': course.lon,
        'book_url': f'https://bookateetime.teequest.com{href}'
      })
    return tee_times
  except Exception as e:
    print(f"[bookateetime] Error with course {course.name}: {e}")
    return []

def search_bookateetime(date, players):
  results = []
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
      executor.submit(fetch_bookateetime, course, date, players)
      for course in courses if course.source == 'bookateetime'
    ]
    for future in as_completed(futures):
      results += future.result()
  return results


# --- GolfBack ---
def fetch_golfback(course, date, players):
  try:
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
    response = requests.post(url, headers=headers, json=params, timeout=10)
    tee_times_raw = response.json().get('data', [])

    tee_times = []
    for tt in tee_times_raw:
      tee_times.append({
        'course': course.name,
        'tee_time': pd.to_datetime(tt['dateTime'], format='%Y-%m-%dT%H:%M:%S%z')
                      .astimezone(pytz.timezone("US/Central")).strftime("%Y-%m-%d %H:%M:%S"),
        'price': float(tt['rates'][0]['price']),
        'players': tt['playersMax'],
        'lat': course.lat,
        'lon': course.lon,
        'book_url': f"https://golfback.com/#/course/{course.id}/date/{date}/teetime/{tt['id']}?rateId={tt['rates'][0]['ratePlanId']}&holes=18&players={players}"
      })
    return tee_times
  except Exception as e:
    print(f"[GolfBack] {course.name} error: {e}")
    return []

def search_golfback(date, players):
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_golfback, c, date, players)
                for c in courses if c.source == 'golfback']
    return [tt for f in as_completed(futures) for tt in f.result()]


# --- ForeUp ---
def fetch_foreup(course, date, players):
  try:
    flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
    url = f"https://foreupsoftware.com/index.php/api/booking/times?time=all&date={flip_date}&holes=all&players={players}&booking_class=14824&schedule_id={course.id}&api_key=no_limits"
    headers = {
      "User-Agent": "Mozilla/5.0",
      "Referer": f"https://foreupsoftware.com/index.php/booking/{course.id}/7340",
      "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=10)
    tee_times_raw = response.json()

    tee_times = []
    for tt in tee_times_raw:
      tee_times.append({
        'course': course.name,
        'tee_time': pd.to_datetime(tt['time'], format='%Y-%m-%d %H:%M')
                      .tz_localize('US/Central').tz_convert('UTC'),
        'price': float(tt['green_fee'] + tt['cart_fee']),
        'players': tt['available_spots'],
        'lat': course.lat,
        'lon': course.lon,
        'book_url': f'https://foreupsoftware.com/index.php/booking/22857/{course.id}#/teetimes'
      })
    return tee_times
  except Exception as e:
    print(f"[ForeUp] {course.name} error: {e}")
    return []

def search_foreup(date, players):
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_foreup, c, date, players)
                for c in courses if c.source == 'foreup']
    return [tt for f in as_completed(futures) for tt in f.result()]

  
def get_tee_times(date, players, coords=None):

  # Filter coordinates within the bounding box
  if coords is None:
    coords = {
      'min_lat': 38.757, 'max_lat': 39.427,
      'min_lon': -94.908, 'max_lon': -94.235
    }

  filtered_courses = [
      course for course in courses
      if coords['min_lat'] <= course.lat <= coords['max_lat'] 
        and coords['min_lon'] <= course.lon <= coords['max_lon']
  ]

  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_bookateetime, c, date, players)
                for c in filtered_courses if c.source == 'bookateetime']
    futures += [executor.submit(fetch_golfback, c, date, players)
                for c in filtered_courses if c.source == 'golfback']
    futures += [executor.submit(fetch_foreup, c, date, players)
                for c in filtered_courses if c.source == 'foreup']
    return [tt for f in as_completed(futures) for tt in f.result()]


if __name__ == "__main__":
  # Example usage
  date = "2025-05-04"
  players = 4
  tee_times = get_tee_times(date, players)
  df = pd.DataFrame(tee_times)
  print(df)
