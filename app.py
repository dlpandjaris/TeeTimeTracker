from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from datetime import datetime
import json
import os
# import tee_time_service
import tee_time_service_threaded


app = Flask(__name__)
CORS(app, resources={r"/tee_times": {"origins": [
  "http://localhost:4200",
  "https://regal-muse-263204.web.app"
]}})

@app.route('/tee_times', methods=['GET', 'OPTIONS'])
def get_tee_times():
  if request.method == 'OPTIONS':
    # CORS preflight
    response = make_response('', 204)
  else:
    date = request.args.get('date', default=datetime.today().strftime('%Y-%m-%d'))
    players = int(request.args.get('players', 4))
    coords = json.loads(request.args.get('coords', default=None))
    tee_times = tee_time_service_threaded.get_tee_times(date, players, coords)
    response = make_response(jsonify(tee_times))

  response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
  response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
  response.headers['Access-Control-Allow-Headers'] = 'Content-Type'    
  return response

if __name__ == '__main__':
  # app.run(debug=True)
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port, debug=True)