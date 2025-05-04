from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
import tee_time_service


app = Flask(__name__)
CORS(app, resources={r"/tee_times": {"origins": [
  "http://localhost:4200",
  "https://regal-muse-263204.web.app"
]}})

@app.route('/tee_times', methods=['GET'])
def get_tee_times():
  date = request.args.get('date', default=datetime.today().strftime('%Y-%m-%d'))
  players = int(request.args.get('players', 4))

  tee_times_df = tee_time_service.get_tee_times(date, players)

  return jsonify(tee_times_df.to_dict(orient='records'))


if __name__ == '__main__':
  # app.run(debug=True)
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port, debug=True)