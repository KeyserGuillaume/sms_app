import unidecode
import re
from overpass_api import get_street_location, get_map_between_points, get_full_map_between_points
from geometry_utils import get_flying_distance
from routing_engine import RoutingEngine, get_required_sms_number
import constants


def get_message_from_itinerary(itinerary):
    result = 'Distance: ' + str(round(itinerary['distance'], 2)) + 'km;'
    for part in itinerary['directions']:
        way_name = (part['way'].replace('Boulevard', 'Bv.')
                              .replace('Avenue', 'Av.')
                              .replace('Rue', 'R.')
        )
        way_name = unidecode.unidecode(way_name[:constants.MAX_CHARS_PER_WAY])
        distance_str = str(round(part['distance']*1000)) + 'm;' if part['distance'] < 1 else str(round(part['distance'], 2)) + 'km;'
        result += '\n' + str(round(part['angle'])) + 'd, ' + way_name + ', ' + distance_str
    print(get_required_sms_number(len(result)), ' is the real required number of sms')
    return result

def routing_engine_wrapper(map_data, pointA, pointB):
    engine = RoutingEngine(False, 0)
    itinerary = engine.dijkstra(map_data, pointA, pointB)
    if itinerary['distance'] == 0:
        return ''
    msg = get_message_from_itinerary(itinerary)
    if get_required_sms_number(len(msg)) <= 2:
        return msg
    else:
        engine = RoutingEngine(True, constants.SMS_TO_METER_PREFERENCE)
        itinerary = engine.dijkstra(map_data, pointA, pointB)
        msg = get_message_from_itinerary(itinerary)
        return msg

def get_walking_itinerary(nA, wayA, cityA, nB, wayB, cityB):
    pointA = get_street_location(nA, wayA, cityA)
    pointB = get_street_location(nB, wayB, cityB)
    #print(pointA)
    #print(pointB)
    distance = get_flying_distance(pointA, pointB)
    #print(distance)
    if distance > constants.MAX_FLYING_DISTANCE:
        return ''
    map_data = get_map_between_points(pointA, pointB)
    msg = routing_engine_wrapper(map_data, pointA, pointB)
    if msg == '':   
        map_data = get_full_map_between_points(pointA, pointB)
        msg = routing_engine_wrapper(map_data, pointA, pointB)
        return msg
    else:
        return msg
    

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
    result = get_walking_itinerary(nA, wayA, cityA, nB, wayB, cityB)
    print(result)
    return result
