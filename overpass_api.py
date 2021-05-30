import requests
import json
import datetime
import re
from geometry_utils import get_flying_distance, get_midpoint

overpass_index = 0
def query_overpass(query):
    # temporary hack used for manual tests
    global overpass_index
    # to be used with following query
    # curl -X POST -F 'Body=Walk from 156 avenue loubet, dunkerque to 168 avenue de la libération' localhost:5000
    # recorded_results = ['overpass_query_18:00:34.313883.json', 'overpass_query_18:00:51.380400.json', 'overpass_query_20:03:23.125522.json']
    # curl -X POST -F 'Body=Walk from 41 rue joseph jacquard, dunkerque to 52 rue pierre et marie curie' localhost:5000
    # recorded_results = ['overpass_query_17:47:21.136546.json', 'overpass_query_17:47:45.812696.json', 'overpass_query_17:47:48.224438.json']
    recorded_results = []
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

def get_street_location(n, way, city):
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
    street_location_query = f"""
    [out:json];
    area[name~"{city_regex}"][postal_code];
    rel[name~"{way_regex}"](area);
    node(r)(if:lrs_in("{n}",t["addr:housenumber"]));
    out;
    """
    point =  query_overpass(street_location_query)['elements'][0]
    return point

def get_map_between_points(pointA, pointB):
    distance = get_flying_distance(pointA, pointB)
    midpoint = get_midpoint(pointA, pointB)
    map_query = f"""
    [out:json];    
    (
      way[highway][foot=yes](around:{1000*distance*0.6},{midpoint['lat']},{midpoint['lon']});
      way[highway~"^(footway|path|pedestrian)$"](around:{distance*0.6},{midpoint['lat']},{midpoint['lon']});
    );
    (._;>;);
    out;
    """
    #print(map_query)
    map_data = query_overpass(map_query)
    return map_data

