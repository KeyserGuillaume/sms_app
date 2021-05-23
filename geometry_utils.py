import math

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

# to the equator I think, and the proper term is bearing
def _get_angle(point1, point2):
    lat1 = radians(point1['lat'])
    lon1 = radians(point1['lon'])
    lat2 = radians(point2['lat'])
    lon2 = radians(point2['lon'])
    
    dLon = (lon2 - lon1);

    y = math.sin(dLon) * math.cos(lat2);
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon);

    brng = math.atan2(y, x);

    brng = 180*brng/math.pi

    brng = brng % 360;

    return brng;


def get_angle(point1, point2, point3):
    return (_get_angle(point1, point2) - 180 - _get_angle(point2, point3)) % 360

def get_midpoint(point1, point2):
    return {
       'lat': (point1['lat'] + point2['lat'])/2.,
       'lon': (point1['lon'] + point2['lon'])/2.
    }

# here we do simple stuff
# we do not try to solve tediously difficult problems on spheres or ellispoids
def get_projection_on_segment(point, segment):
    segpoint1 = segment[0]
    segpoint2 = segment[1]
    
    # project on plane tangent of earth at point (at least that's what I'm trying to do)
    proj1 = [
        radians(segpoint1['lat']) - radians(point['lat']),
        math.cos(radians(point['lat'])) * (radians(segpoint1['lon']) - radians(point['lon']))
    ]
    proj2 = [
        radians(segpoint2['lat']) - radians(point['lat']),
        math.cos(radians(point['lat'])) * (radians(segpoint2['lon']) - radians(point['lon']))
    ]
    
    # find the projection
    t = ((proj2[0] - proj1[0])*proj2[0] + (proj2[1] - proj1[1])*proj2[1]) / ((proj1[0] - proj2[0])**2 + (proj1[1] - proj2[1])**2)
    if t > 1:
        t = 1
    if t < 0:
        t = 0

    projection = {
        'lat': t * segpoint1['lat'] + (1-t) * segpoint2['lat'],
        'lon': t * segpoint1['lon'] + (1-t) * segpoint2['lon']
    }

    return projection
