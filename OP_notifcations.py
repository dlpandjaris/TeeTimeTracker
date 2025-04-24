from playwright.sync_api import sync_playwright
from email_me import make_email, send_email
import time
import argparse

parser = argparse.ArgumentParser(description="A script to monitor for Tee Times at Overland Park Golf Courses.")

parser.add_argument('day', type=int, help="Day of Month")

args = parser.parse_args()

day = args.day if args.day is not None else 14
players = 4
start_time = 10
end_time = 15
timeout_hours = 12

class TeeTime():
  def __init__(self, raw_tee_time):
    self.raw_tee_time = raw_tee_time
    self.start_time = self.raw_tee_time['startTime']
    self.greens_fee = self.raw_tee_time['shItemPrices'][0]['displayPrice']
    self.cart_fee = self.raw_tee_time['shItemPrices'][1]['displayPrice']
    self.full_price = self.greens_fee + self.cart_fee
    self.course_name = self.raw_tee_time['courseName']
    self.tee_sheet_id = self.raw_tee_time['teeSheetId']

with sync_playwright() as p:
  browser = p.chromium.launch(headless=False)  # Launch browser
  page = browser.new_page()

  tee_times = {}
  # Define a callback to capture responses
  def capture_teetimes(response):
    if "TeeTimes" in response.url:
      raw_tee_times = response.json()

      if len(raw_tee_times) > 0 and type(raw_tee_times) == list:
        print("Tee Times Available")
        message = ''
        tee_times = {}
        for tt in raw_tee_times:
          tee_time = TeeTime(tt)
          tee_times[tee_time.tee_sheet_id] = tee_time
          message += f"Tee Time: {tee_time.start_time}\n"
          message += f"Greens Fee: ${tee_time.full_price}\n"
          message += f"Course: {tee_time.course_name}\n\n"
        print(message)
        email = make_email(message)
        send_email(email)

  # Navigate to the page
  page.goto(f"https://overland.cps.golf/onlineresweb/search-teetime?TeeOffTimeMin={start_time}&TeeOffTimeMax={end_time}")

  # Fill in search Criteria
  page.click('div.course-filter-control')
  page.click('span.mat-option-text:has-text("Par-3")')
  page.click('span.mat-button-wrapper:has-text("Done")')
  time.sleep(0.25)

  page.click(f'span.day-background-upper:has-text("{day}")')

  page.click(f'span.mat-button-toggle-label-content:has-text("{players}")')

  page.click('div.hole-filter-control')
  page.click('span.mat-option-text:has-text("18 Holes")')

  # Add the event listener for responses
  page.on("response", capture_teetimes)

  # {'teeSheetId': 1876968, 'startTime': '2024-12-05T07:57:00', 'courseTimeId': 66664, 'startingTee': 1, 'crossOverTeeSheetId': 0, 'participants': 4, 'courseId': 3, 'courseDate': '2024-12-05T00:00:00', 'defaultRateCode': 'NPOP', 
  # 'defaultBookingRate': {'rateCode': 'NPOP', 'bookingRateType': 4, 'bookingRateTypeName': 'MemberRate'}, 'teeTypeId': 1, 'holes': 18, 'defaultHoles': 0, 'siteId': 2, 'courseName': 'North ', 'courseNameIncludeCrossOver': 'North ', 'shItemPrices': [{'itemGuid': 'a2973245-3e36-4a56-a675-ebec31f953fc', 'shItemCode': 'GreenFee18Online', 'itemCode': '30', 'price': 28.0, 'displayPrice': 28.0, 'taxInclusivePrice': 28.0, 'taxCode': 'N/A', 'itemDesc': 'GF WEEKDAY', 'classCode': 'R', 'rateCode': 'NPOP', 'currentPrice': 28.0, 'priceType': 1, 'priceTypeName': 'ClassPrice'}, {'itemGuid': '7ce7c696-b56a-4bc1-9db7-1b06cdb417ca', 'shItemCode': 'FullCart18Online', 'itemCode': '70', 'price': 15.5464, 'displayPrice': 15.5464, 'taxInclusivePrice': 17.0, 'taxCode': 'KSTX', 'itemDesc': '18 HOLE 1/2 RIDING CART', 'classCode': 'R', 'rateCode': 'NPOP', 'currentPrice': 15.5464, 'priceType': 1, 'priceTypeName': 'ClassPrice'}], 'shItemPricesGroup': [], 'holesDisplay': '9 or 18', 'playersDisplay': '1 - 4 GOLFERS', 'minPlayer': 1, 'maxPlayer': 4, 'availableParticipantNo': [1, 2, 3, 4], 'summaryDetail': {}, 'playersRateCode': [], 'isIncludeCartPriceInPreview': True, 'isShowSeparateGreenCartFee': True, 'playerNames': [], 'blockTexts': [], 'allowSpecialTeetimeClassCodes': [], 'isShowCartDetail': True, 'isContain9HoleItems': True, 'isContain18HoleItems': True, 'bookingNotes': [], 'defaultClassCode': '03', 'teeSuffix': ' '}

  # Wait for some time or perform additional actions
  page.wait_for_timeout(timeout_hours * 3600000)

  # Close the browser
  browser.close()