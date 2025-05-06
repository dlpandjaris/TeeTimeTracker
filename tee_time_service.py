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

def get_tee_times(date, players):
  """
  Get tee times for a given date and number of players from various golf courses.
  
  Args:
      date (str): The date for which to get tee times in 'YYYY-MM-DD' format.
      players (int): The number of players.

  Returns:
      list[dict]: A list of tee time dictionaries.
  """
  tee_times = []

  # Collect tee times from each source
  tee_times += search_bookateetime(date, players)
  tee_times += search_golfback(date, players)
  tee_times += search_foreup(date, players)

  return tee_times

def search_bookateetime(date, players):
  tee_times = []
  for course in courses:
    if course.source == 'bookateetime':
      # Make a GET request to the URL with the course name and date
      response = requests.get(f"https://bookateetime.teequest.com/search/{course.id}/{date}?selectedPlayers={players}&selectedHoles=18")

      # Decode the response content as a string
      content_str = response.content.decode('utf-8')
      soup = BeautifulSoup(content_str, 'html.parser')

      for tee_time_div in soup.find_all('div', class_='tee-time'):
        href = tee_time_div.find('a', class_='btn')['href']
        tt = {
          'course': course.name,
          'tee_time': pd.to_datetime(tee_time_div['data-date-time'], format='%Y%m%d%H%M').tz_localize('US/Central').tz_convert('UTC'),
          'price': float(tee_time_div['data-price']),
          'players': int(tee_time_div['data-available']),
          'lat': course.lat,
          'lon': course.lon,
          'book_url': f'https://bookateetime.teequest.com{href}'
        }
        tee_times.append(tt)
    
  return tee_times

def search_golfback(date, players):
  tee_times = []
  for course in courses:
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

  return tee_times


def search_foreup(date, players):
  tee_times = []
  for course in courses:
    if course.source == 'foreup':
      flip_date = datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d-%Y')
      url = f"https://foreupsoftware.com/index.php/api/booking/times?time=all&date={flip_date}&holes=all&players={players}&booking_class=14824&schedule_id={course.id}&api_key=no_limits"
      headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://foreupsoftware.com/index.php/booking/{course.id}/7340",
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
          'tee_time': pd.to_datetime(tee_time['time'], format='%Y-%m-%d %H:%M') \
            .tz_localize('US/Central').tz_convert('UTC'),
          'price': float(tee_time['green_fee'] + tee_time['cart_fee']),
          'players': tee_time['available_spots'],
          'lat': course.lat,
          'lon': course.lon,
          'book_url': f'https://foreupsoftware.com/index.php/booking/22857/{course.id}#/teetimes'
        }
        tee_times.append(tt)

  return tee_times


if __name__ == "__main__":
  # Example usage
  date = "2025-05-04"
  players = 4
  tee_times_df = get_tee_times(date, players)
