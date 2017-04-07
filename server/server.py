import os
import time
import json
import requests

from datetime import datetime
from bs4 import BeautifulSoup
from werkzeug.routing import BaseConverter

from flask import Flask, request, render_template, url_for
from pymemcache.client.base import Client as MemcachedClient


##########################################################
#   SETUP
#   setup the flask application, the cache, and set an API key
##########################################################

app = Flask(__name__)
cache = MemcachedClient(('localhost',11211))
api_key = os.environ['MY_API_KEY']
open_weather_api_key = os.environ['OPEN_WEATHER_API_KEY']


##########################################################
#   Helper Functions
##########################################################

# allows routes to match regular expressions
class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]
app.url_map.converters['regex'] = RegexConverter


##########################################################
#   Homepage
#   render a template site, really just sugar on top
#   see http://flask.pocoo.org/
#   also http://flask.pocoo.org/docs/0.12/templating/
##########################################################
@app.route('/')
@app.route('/<regex("[A-Za-z0-9-_/.]{1,40}"):req>')
def hello(req=""):
    if 'breadfactorystudios' in request.url:
        return render_template('home.html',bfs=True), 200
    return render_template('home.html',bfs=False), 200


##########################################################
#   WEATHER FORECAST
#   for getting the weather forecast for a city or a US zip code
##########################################################
@app.route('/api/v1/getforecastcity', methods=['GET'])
def get_forecast_city():
    # pull from cache first
    city = request.args.get('q','Philadelphia')
    saved_forecast = cache.get('forecastcity'+city)

    if saved_forecast:
        return saved_forecast.decode('utf-8')

    # get the values from the query parameters. e.g. mysite.com/api/v1/getforecast?q=19147
    response = requests.get('http://api.openweathermap.org/data/2.5/weather?q='+city+'&APPID='+open_weather_api_key, timeout=10)

    # get the information from the JSON that was returned to us, if there was any
    weather_dictionary = {}
    if response.json():
        weather_dictionary = response.json()

    # format the information so we can process it, convert the temp to F from K
    return_dictionary = {
        "des" : '' if len(weather_dictionary.get("weather",[{}])) < 1 else weather_dictionary.get("weather",[{}])[0].get("description",""),
        "temp" : '' if weather_dictionary.get("main",{}).get("temp") is None else int(int(weather_dictionary.get("main",{}).get("temp",0)) * 9/5 - 459.67)
    }

    # set cache for an hour
    cache.set('forecastcity'+city,json.dumps(return_dictionary),3600)

    return json.dumps(return_dictionary)

@app.route('/api/v1/getforecastzip', methods=['GET'])
def get_forecast_zip():
    # pull from cache first
    zip_code = request.args.get('q','19147')
    saved_forecast = cache.get('forecastzip'+zip_code)

    if saved_forecast:
        return saved_forecast.decode('utf-8')

    # get the values from the query parameters. e.g. mysite.com/api/v1/getforecastzip?q=19147
    response = requests.get('http://api.openweathermap.org/data/2.5/weather?zip='+zip_code+',us&APPID='+open_weather_api_key, timeout=10)

    # get the information from the JSON that was returned to us, if there was any
    weather_dictionary = {}
    if response.json():
        weather_dictionary = response.json()

    # format the information so we can process it, convert the temp to F from K
    return_dictionary = {
        "des" : '' if len(weather_dictionary.get("weather",[{}])) < 1 else weather_dictionary.get("weather",[{}])[0].get("description",""),
        "temp" : '' if weather_dictionary.get("main",{}).get("temp") is None else int(int(weather_dictionary.get("main",{}).get("temp",0)) * 9/5 - 459.67)
    }

    # set cache for an hour
    cache.set('forecastzip'+zip_code,json.dumps(return_dictionary),3600)

    return json.dumps(return_dictionary)


##########################################################
#   STOCK QUOTE
#   for getting a stock quote for a certain symbol e.g. "AAPL"
#########################################################
@app.route('/api/v1/getstockquote', methods=['GET'])
def get_stock():
    # get the values from the query parameters. e.g. mysite.com/api/v1/getstockquote?q=AAPL
    symbol = request.args.get('s','AAPL')

    # pull from cache first
    saved_quote = cache.get('stock'+symbol)

    if saved_quote:
        return saved_quote.decode('utf-8')

    return_dictionary = {
        "price":"",
        "dir": ""
    }

    user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    source_url = 'http://www.nasdaq.com/symbol/'+symbol+'/real-time'
    response = requests.get(source_url, timeout=10, headers={
        'User-agent': user_agent})

    doc = BeautifulSoup(response.text,'html.parser')

    prices = doc.select('div[id="qwidget_lastsale"]')
    arrows = doc.select('div[id="qwidget-arrow"]')

    if len(prices) > 0 and len(arrows) > 0:
        return_dictionary = {
            "price":prices[0].getText().strip(),
            "dir": 'down' if 'red' in str(arrows[0]) else 'up'
        }

    # set cache for an hour
    cache.set('stock'+symbol,json.dumps(return_dictionary),600)

    return json.dumps(return_dictionary)


##########################################################
#   BASEBALL STANDINGS
#   for getting a stock quote for a certain symbol e.g. "AAPL"
#########################################################
@app.route('/api/v1/getmlbstandings', methods=['GET'])
def get_mlb_standings():
    # get the values from the query parameters. e.g. mysite.com/api/v1/getmlbstandings?t=philadelphis
    team = request.args.get('t','philadelphia')

    # pull from cache first
    saved_stats = cache.get('mlb'+team)

    if saved_stats:
        return saved_stats.decode('utf-8')

    return_dictionary = {
        "STRK":"",
        "W":"",
        "L":"",
        "GB":""}

    user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    source_url = 'http://www.cbssports.com/mlb/standings'
    response = requests.get(source_url, timeout=10, headers={
        'User-agent': user_agent})

    doc = BeautifulSoup(response.text,'html.parser')

    trs = doc.select('tr')

    columns = ["TEAM","W","L","PCT","GB","RS","RA","DIFF","HOME","ROAD","EAST","CENT","WEST","L10","STRK"]

    for tr in trs:
        if team.lower() in str(tr).lower():
            tds = tr.select('td')
            w_index = columns.index('W')
            l_index = columns.index('L')
            gb_index = columns.index('GB')
            strk_index = columns.index('STRK')
            if len(tds) >= max([w_index,l_index,gb_index,strk_index]):
                return_dictionary = {
                    "W":tds[w_index].getText().strip(),
                    "L":tds[l_index].getText().strip(),
                    "GB":tds[gb_index].getText().strip(),
                    "STRK":tds[strk_index].getText().strip()
                    }

    # set cache for an hour
    cache.set('mlb'+team,json.dumps(return_dictionary),600)

    return json.dumps(return_dictionary)


##########################################################
#   LIGHT ALARM
#   for setting and controlling a light-based alarm
##########################################################
@app.route('/api/v1/setalarm', methods=['GET'])
def set_alarm():
    # Set the alarm via query params h and m, as well as a secret key
    # get the values from the query parameters. e.g. mysite.com/api/v1/set-alarm?h=6&m=30&key=secret
    hour = request.args.get('h'),
    minute = request.args.get('m')
    key = request.args.get('key')

    if key == api_key:

        # if hour and minute are numbers then save them to the cache
        if hour and minute:
            hour = hour[0]  # some strange tuple bug with flask
            if hour.isdigit() and minute.isdigit():
                hour = int(hour)
                minute = int(minute)
                if hour >= 0 and hour < 24 and minute >= 0 and minute < 60:
                    data_to_save = {
                        'hour': hour,
                        'minute': minute
                    }
                    cache.set('alarm', json.dumps(data_to_save))
                    return "SUCCESS: alarm set for %s:%s" % (hour, minute)

    return "error"

# Get the status of the alarm (called from something like an arduino)
@app.route('/api/v1/getalarm')
def get_alarm():
    saved_time = cache.get('alarm')

    if saved_time:
        # decode and parse the json from the cache, if there's any available
        saved_time_dict = json.loads(saved_time.decode('utf-8'))
        alarm_start_hour = int(saved_time_dict['hour'])
        alarm_start_minute = int(saved_time_dict['minute'])

        # we want the alarm to be on for 30 minutes
        if alarm_start_minute >= 30:
            alarm_end_hour = alarm_start_hour + 1
            alarm_end_minute = (alarm_start_minute + 30) % 60
        else:
            alarm_end_hour = alarm_start_hour
            alarm_end_minute = alarm_start_minute + 30

        # get the current hour and minute
        current_hour = int(datetime.now().strftime('%H'))
        current_minute = int(datetime.now().strftime('%M'))

        current_time_in_minutes = current_hour * 60 + current_minute
        alarm_start_in_minutes = alarm_start_hour * 60 + alarm_start_minute
        alarm_end_in_minutes = alarm_end_hour * 60 + alarm_end_minute
        if alarm_start_in_minutes <= current_time_in_minutes <= alarm_end_in_minutes:
            return 'ON'

        return "time is %d:%d alarm starts at %d:%d and ends at %d:%d" % (
            current_hour, current_minute, alarm_start_hour, alarm_start_minute, alarm_end_hour, alarm_end_minute)

    return 'NOT SET'


##########################################################
#   TEMPERATURE SENSOR
#   for setting and controlling a light-based alarm
##########################################################
@app.route('/api/v1/settemp', methods=['GET'])
def set_temperature():
    # set the temperature (called from something like an arduino)
    # get the values from the query parameters. e.g. mysite.com/api/v1/settemp?t=21&h=30
    temp = request.args.get('t'),
    humidity = request.args.get('h')

    cache.set('temp', json.dumps({"temp":temp,"humidity":humidity}))

    return "TEMPOK"

# get the current temperature (can use to populate a dashboard or view directly in a browser)
@app.route('/api/v1/gettemp', methods=['GET'])
def get_temperature():
    # get the values from the query parameters. e.g. mysite.com/api/v1/set-alarm?h=6&m=30
    return cache.get('temp')


##########################################################
#   MAIN
#   don't edit this unless you know what you're doing :)
##########################################################

# The "main" function, to run the server
if __name__ == '__main__':
    app.run(host='0.0.0.0')