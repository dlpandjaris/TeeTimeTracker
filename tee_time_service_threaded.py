from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import json
import re
from dateutil import parser

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
      # Find the span that contains "holes with cart"
      holes_span = tee_time_div.find('span', string=re.compile(r'\d+\s+holes'))

      # Extract number from the text
      holes = int(re.search(r'\d+', holes_span.text).group()) if holes_span else None

      href = tee_time_div.find('a', class_='btn')['href']
      tee_times.append({
        'course': course.name,
        'tee_time': pd.to_datetime(tee_time_div['data-date-time'], format='%Y%m%d%H%M')
                      .tz_localize('US/Central').tz_convert('UTC'),
        'price': float(tee_time_div['data-price']),
        'players': int(tee_time_div['data-available']),
        'holes': holes,
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
        'holes': max(tt['holes']),
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
        'holes': tt['holes'],
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
  

# --- CPS ---
def fetch_cps(course, date, players):
  try:
    session = requests.Session()

    # Step 1: Start session and visit homepage to get cookies
    homepage_url = f"https://{course.id}.cps.golf/onlineresweb/"
    session.get(homepage_url)

    flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
    url = f'https://{course.id}.cps.golf/onlineres/onlineapi/api/v1/onlinereservation/TeeTimes?searchDate={flip_date}&holes=0&numberOfPlayer={players}&courseIds=3,5,2,1,4&searchTimeType=0&teeOffTimeMin=0&teeOffTimeMax=23&isChangeTeeOffTime=true&teeSheetSearchView=5&classCode=R&defaultOnlineRate=N&isUseCapacityPricing=false&memberStoreId=1&searchType=1'

    # Step 2: Make API request with cookies now in session
    headers = {
      'client-id': 'onlineresweb',
      'x-apikey': '8ea2914e-cac2-48a7-a3e5-e0f41350bf3a',
      'x-siteid': '4',
      'x-componentid': '1',
      'x-moduleid': '7',
      'x-productid': '1',
      'x-terminalid': '3',
      'x-timezone-offset': '0',
      'x-timezoneid': 'UTC',
      'x-websiteid': '193dc026-6acc-4aac-3af7-08db7f14aeec',
      'referer': f'https://{course.id}.cps.golf/onlineresweb/search-teetime',
      'user-agent': 'Mozilla/5.0',
    }

    response = session.get(url, headers=headers)
    tee_times_raw = response.json()

    central = pytz.timezone("America/Chicago")

    tee_times = []
    for tee_time in tee_times_raw:
      tt = {
        'course': f"{course.name} - {tee_time['courseName']}",
        'tee_time': central.localize(parser.isoparse(tee_time['startTime'])).astimezone(pytz.utc).isoformat(),
        'price': sum({float(p['displayPrice']) for p in tee_time['shItemPrices']}),
        'players': tee_time['maxPlayer'],
        'holes': tee_time['holes'],
        'lat': course.lat,
        'lon': course.lon,
        'book_url': f'https://{course.id}.cps.golf/onlineresweb/teetime/checkout?id={tee_time['teeSheetId']}&holes=0&numberOfPlayer=0&loginAfterBookTeeTime=true'
      }
      tee_times.append(tt)
    
    return tee_times
  except Exception as e:
    print(f"[CPS] {course.name} error: {e}")
    return []
  
def search_cps(date, players):
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_cps, c, date, players)
                for c in courses if c.source == 'cps']
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
    futures += [executor.submit(fetch_cps, c, date, players)
                for c in filtered_courses if c.source == 'cps']
    return [tt for f in as_completed(futures) for tt in f.result()]


if __name__ == "__main__":
  # Example usage
  date = "2025-05-04"
  players = 4
  tee_times = get_tee_times(date, players)
  df = pd.DataFrame(tee_times)
  print(df)
