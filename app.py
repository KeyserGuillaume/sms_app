import os
from flask import Flask, request, redirect

from contextlib import closing
from urllib.request import urlopen
import requests
import dateutil.parser
import json
import datetime

import re

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

import math
from queue import PriorityQueue

app = Flask(__name__)

# Find these values at https://twilio.com/user/account
twilio_sid = os.environ['TWILIO_ACCOUNT_SID']
twilio_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(twilio_sid, twilio_token)

################# weather ####################
# https://api.meteo-concept.com
weather_token = os.environ['WEATHER_TOKEN']
def will_it_rain(request):
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

################ overpass queries ############################

overpass_index = 0
def query_overpass(query):
    global overpass_index
    # to be used with following query
    # curl -X POST -F 'Body=Walk from 156 avenue loubet, dunkerque to 168 avenue de la libération' localhost:5000
    recorded_results = ['overpass_query_18:00:34.313883.json', 'overpass_query_18:00:51.380400.json', 'overpass_query_20:03:23.125522.json']
    if overpass_index < len(recorded_results):
        with open(recorded_results[overpass_index]) as json_file:
            result = json.load(json_file)
        overpass_index += 1
        return result
    overpass_url = "http://overpass-api.de/api/interpreter";
    response = requests.get(overpass_url, params={'data': query})
    data = response.json()
    with open(f'overpass_query_{str(datetime.datetime.now().time())}.json', 'w') as outfile:
        json.dump(data, outfile)
    return data

def prepare_letter_for_regex(letter, capitalize):
    if letter == 'a':
        lowers = 'aàáâä'
        uppers = 'AÀÁÂÄ'
    elif letter == 'e':
        lowers = 'eéèêë'
        uppers = 'eÉÈÊË'
    elif letter == 'u':
        lowers = 'uúùûü'
        uppers = 'UÚÙÛÜ'
    elif letter == 'i':
        lowers = 'iìíîï'
        uppers = 'IÍÌÎÏ'
    elif letter == 'o':
        lowers = 'oòóôö'
        uppers = 'OÒÓÔÖ'
    else:
        lowers = letter.lower()
        uppers = letter.upper()
    if capitalize:
        return '[' + lowers + uppers + ']'
    elif len(lowers) > 1:
        return '[' + lowers + ']'
    else:
        return letter

def prepare_noun_for_regex(noun):
    if noun in ['rue', 'boulevard', 'voie', 'avenue', 'chemin', 'passage']:
        return '[' + noun[0].upper() + noun[0] + ']' + noun[1:]
    letters = list(noun)
    letters[0] = prepare_letter_for_regex(letters[0], True)
    for i in range(1, len(letters)):
        letters[i] = prepare_letter_for_regex(letters[i], False)
    return ''.join(letters)

def get_location_query(n, way, city):
    city_nouns = re.split("-|'| ", city.lower())
    city_nouns = [prepare_noun_for_regex(noun) for noun in city_nouns if len(noun) > 3]
    city_regex = '.*'.join(city_nouns)
    way_nouns = re.split("-|'| ", way.lower())
    way_nouns = [noun if noun not in ['bd', 'bv'] else 'boulevard' for noun in way_nouns ]
    way_nouns = [prepare_noun_for_regex(noun) for noun in way_nouns if len(noun) > 3 or noun == 'rue']
    way_regex = '.*'.join(way_nouns)    

    # it must have a postal code otherwise in Paris for example I get results
    # from the 'préfecture de police de Paris' area which is Île-de-France.
    # we assume also that the node might be tagged with several housenumbers so we use lrs_in.
    return f"""
    [out:json];
    area[name~"{city_regex}"][postal_code];
    rel[name~"{way_regex}"](area);
    node(r)(if:lrs_in("{n}",t["addr:housenumber"]));
    out;
    """

def get_query_for_map(pointA, pointB):
    distance = get_flying_distance(pointA, pointB)
    midpoint = get_midpoint(pointA, pointB)
    return f"""
    [out:json];    
    (
      way[highway][foot=yes](around:{1000*distance*0.6*2},{midpoint['lat']},{midpoint['lon']});
      way[highway~"^(footway|path|pedestrian)$"](around:{distance*0.6},{midpoint['lat']},{midpoint['lon']});
    );
    (._;>;);
    out;
    """

##################### geometry #######################

def radians(x):
    return math.pi*x/180.

def degrees(x):
    return 180.*x/math.pi

def get_flying_distance(point1, point2):
    R = 6370
    lat1 = radians(point1['lat'])
    lon1 = radians(point1['lon'])
    lat2 = radians(point2['lat'])
    lon2 = radians(point2['lon'])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return distance

# to the equator I think
def _get_angle(point1, point2):
    print(get_flying_distance(point1, point2))
    lat1 = radians(point1['lat'])
    lon1 = radians(point1['lon'])
    lat2 = radians(point2['lat'])
    lon2 = radians(point2['lon'])
    
    dLon = (lon2 - lon1);

    y = math.sin(dLon) * math.cos(lat2);
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon);

    brng = math.atan2(y, x);

    brng = brng % 360;

    print(brng)

    return brng;

def get_angle(point1, point2, point3):
    return (_get_angle(point1, point2) - 180 - _get_angle(point2, point3)) % 360

def get_midpoint(point1, point2):
    return {
       'lat': (point1['lat'] + point2['lat'])/2.,
       'lon': (point1['lon'] + point2['lon'])/2.
    }

##################### itinerary ######################

def compute_neighbors(nodes, ways, pointA, pointB):
    for way in list(ways.values()):
        for i in range(1, len(way['nodes'])):
            node1Id = way['nodes'][i-1]
            node2Id = way['nodes'][i]
            node1 = nodes[node1Id]
            node2 = nodes[node2Id]
            distance = get_flying_distance(node1, node2)
            if 'neighbors' in node1:
                node1['neighbors'].append({'distance': distance, 'node': node2, 'way': way['id']})
            else:
                node1['neighbors'] = [{'distance': distance, 'node': node2, 'way': way['id']}]
            if 'neighbors' in node2:
                node2['neighbors'].append({'distance': distance, 'node': node1, 'way': way['id']})
            else:
                node2['neighbors'] = [{'distance': distance, 'node': node1, 'way': way['id']}]
    foundSource = False
    foundTarget = False    
    for node in list(nodes.values()):
        if node['id'] == pointA['id']:
            pointA['neighbors'] = node['neighbors']
            node['isSource'] = True
            foundSource = True
            source = pointA
    for node in list(nodes.values()):
        if node['id'] == pointB['id']:
            node['isTarget'] = True
            foundTarget = True
    if not foundSource:
        _min = 10
        for node in list(nodes.values()):
            d = get_flying_distance(node, pointA)
            if d < _min:
                _min = d
                _argmin = node
        _argmin['isSource'] = True
        pointA['neighbors'] = _argmin['neighbors']
        source = _argmin
    if not foundTarget:
        _min = 10
        for node in list(nodes.values()):
            d = get_flying_distance(node, pointB)
            if d < _min:
                _min = d
                _argmin = node
        _argmin['isTarget'] = True
     
    return source

def mark_next_point(nodes, distances, markings):
    distanceToA, node, predecessor = distances.get()
    #print(node)
    if node['id'] in markings:
        return None
    # print(distanceToA)
    node['distance'] = distanceToA
    node['predecessor'] = predecessor
    if node['predecessor'] and node['predecessor']['id'] == node['id']:
        print('pb')
    for link in node['neighbors']:
        if not predecessor or link['node']['id'] != predecessor['id']:
            distances.put((distanceToA + link['distance'], link['node'], node))

    markings[node['id']] = True
    return node;

def get_node_path(node):
    if node['predecessor'] and node['predecessor']['id'] == node['id']:
        print('pb')
    path = []
    current_node = node
    i = 0
    while current_node and 'isSource' not in current_node and current_node['predecessor'] and i <= 1000:
        current_node = current_node['predecessor']
        path.append(current_node)
        i+=1
    if i == 1000:
        print('big trouble')
    if 'isSource' not in current_node:
        print('where is source ?')
    #print([x['id'] for x in path])
    print(f'path has length {len(path)}')
    return path[::-1]

def get_actual_directions(path, nodes, ways, pointA):
    directions = []
    previous_node = pointA
    for i in range(1, len(path)):
        node1 = path[i-1]
        node2 = path[i]
        link = [n for n in node1['neighbors'] if n['node']['id'] == node2['id']][0]
        way = ways[link['way']]
        name = way['tags']['name'] if 'name' in way['tags'] else way['tags']['highway']
        if len(directions) == 0 or directions[-1]['way'] != name:
            print(name)
            angle = get_angle(previous_node, node1, node2)
            directions.append({'way': name, 'angle': angle ,'distance': link['distance']})
        else:
            directions[-1]['distance'] += link['distance']
        previous_node = node1
    return directions


def dijkstra(map_data, pointA, pointB):
    elements = map_data['elements']
    print(len(elements))
    nodes = {x['id']: x for x in elements if x['type'] == 'node'}
    print(len(nodes))
    ways = {x['id']: x for x in elements if x['type'] == 'way'}
    print(len(ways))
    source = compute_neighbors(nodes, ways, pointA, pointB)
    print(get_flying_distance(source, pointA))
    pointA['isSource'] = True
    markings = {};
    distances = PriorityQueue()
    distances.put((0, source, None))
    while not distances.empty():
        node = mark_next_point(nodes, distances, markings)
        if node and 'isTarget' in node:
            print('path was found')
            distance = node['distance']
            print(distance)
            path = get_node_path(node)            
            return {
                'distance': distance,
                'directions': get_actual_directions(path, nodes, ways, pointA)
            }
    print('Path not found')
    return {'distance': 0, 'directions': []}

MAX_FLYING_DISTANCE = 30

def get_message_from_itinerary(itinerary):
    result = 'Distance: ' + str(round(itinerary['distance'], 2)) + ';'
    for part in itinerary['directions']:
         result += '\n' + str(round(part['angle'])) + 'd, ' + part['way'] + ', ' + str(round(part['distance'], 2)) + 'km;'
    return result

def get_walking_itinerary(nA, wayA, cityA, nB, wayB, cityB):
    queryA = get_location_query(nA, wayA, cityA)    
    #print(queryA)
    pointA = query_overpass(queryA)['elements'][0]
    queryB = get_location_query(nB, wayB, cityB)
    #print(queryB)
    pointB = query_overpass(queryB)['elements'][0]
    #print(pointA)
    #print(pointB)
    distance = get_flying_distance(pointA, pointB)
    #print(distance)
    if distance > MAX_FLYING_DISTANCE:
        return ''
    map_query = get_query_for_map(pointA, pointB)
    #print(map_query)
    map_data = query_overpass(map_query)
    itinerary = dijkstra(map_data, pointA, pointB)
    if itinerary['distance'] == 0:   
        return ''
    return get_message_from_itinerary(itinerary)
    

def get_walking_itinerary_response(request):
    matchObj = re.match( r'Walk from ([0-9]+) (.*), (.*) to ([0-9]+) (.*), (.*)', request, re.M|re.I)
    if matchObj:
        nA = matchObj.group(1)
        wayA = matchObj.group(2)
        cityA = matchObj.group(3)
        nB = matchObj.group(4)
        wayB = matchObj.group(5)
        cityB = matchObj.group(6)
    if not matchObj:
        matchObj = re.match( r'Walk from ([0-9]+) (.*), (.*) to ([0-9]+) (.*)', request, re.M|re.I)
        nA = matchObj.group(1)
        wayA = matchObj.group(2)
        cityA = matchObj.group(3)
        nB = matchObj.group(4)
        wayB = matchObj.group(5)
        cityB = cityA
    print(get_walking_itinerary(nA, wayA, cityA, nB, wayB, cityB))
    return ''
        

@app.route("/", methods=['POST'])
def incoming_sms():
    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
    message = ''

    # Determine the right reply for this message
    if body == 'Hello':
        # Start our TwiML response
        message = 'Hi'
    elif body[:12] == 'Will it rain':
        message = will_it_rain(body)
    elif body[:9] == 'Walk from':
        message = get_walking_itinerary_response(body)
        
    if message and message != '':
        resp = MessagingResponse()
        resp.message(message)
        return str(resp)
    else:
        return '', 200


if __name__ == "__main__":
    app.run()
