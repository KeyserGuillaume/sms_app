import os
import re
from contextlib import closing
from urllib.request import urlopen
import dateutil.parser

import json

# see https://api.meteo-concept.com

weather_token = os.environ['WEATHER_TOKEN']
def get_rain_response(request):
    insee = ''
    matchObj = re.match( r'Will it rain at ([0-9]{5}) ?', request, re.M|re.I)
    if matchObj:
        insee = matchObj.group(1)
    if not insee:
        matchObj = re.match( r'Will it rain at [Pp]aris ([0-9]{1,2}) ?', request, re.M|re.I)
        if matchObj:
            insee = int(matchObj.group(1)) + 75100
    if not insee:
        matchObj = re.match( r'Will it rain at (\w*) ?', request, re.M|re.I)
        if matchObj:
            city = matchObj.group(1)    
            url = 'https://api.meteo-concept.com/api/location/cities?token={}&search={}'.format(weather_token, city)
            print(url)
            with closing(urlopen(url)) as f:
                insee = json.loads(f.read())['cities'][0]['insee']
    if not insee:
        return ''
    message = ''
    send = False
    url = 'https://api.meteo-concept.com/api/forecast/nextHours?token={}&insee={}'.format(weather_token, insee)
    with closing(urlopen(url)) as f:
        forecast = json.loads(f.read())['forecast']
        for f in forecast:
            time = dateutil.parser.parse(f['datetime']).strftime('%H:%M  ')
            message += '\n' + ('probarain = {} at {}'.format(f['probarain'], time)).strip()
            if f['probarain'] >= 20:
                send = True
    if send:
        return message
    else:
        return ''

