from dataclasses import dataclass, field
from queue import PriorityQueue
from geometry_utils import get_flying_distance, get_projection_on_segment, get_angle, get_bearing_at_node
import constants
import math

class Marking:
    def __init__(self, node_id, distance_from_A, sms_character_count, preceding_marking, preceding_way):
        self.node_id = node_id                        # int
        self.distance_from_A = distance_from_A         # float
        self.sms_character_count = sms_character_count # int
        self.preceding_marking = preceding_marking     # Mark
        self.preceding_way = preceding_way              # int

    def __gt__(self, other):
        return self.node_id > other.node_id

@dataclass(order=True)
class PrioritizedItem:
    score: int
    item: object = field()

def get_required_sms_number(character_count):
    return math.ceil(
        (character_count - constants.TWILIO_MESSAGE_CHARACTER_COUNT) / float(constants.MAX_SMS_CHARACTER_COUNT))

def get_score(distance, character_count):
    return get_required_sms_number(character_count) * constants.SMS_TO_METER_PREFERENCE + distance

def compute_neighbors(nodes, ways, pointA, pointB):
    for way in list(ways.values()):
        for i in range(1, len(way['nodes'])):
            node1Id = way['nodes'][i-1]
            node2Id = way['nodes'][i]
            node1 = nodes[node1Id]
            node2 = nodes[node2Id]
            distance = get_flying_distance(node1, node2)
            node2_as_neighbor = {'distance': distance, 'node': node2, 'way': way['id']}
            if 'neighbors' in node1:
                node1['neighbors'].append(node2_as_neighbor)
            else:
                node1['neighbors'] = [node2_as_neighbor]
            node1_as_neighbor = {'distance': distance, 'node': node1, 'way': way['id']}
            if 'neighbors' in node2:
                node2['neighbors'].append(node1_as_neighbor)
            else:
                node2['neighbors'] = [node1_as_neighbor]
    
    # locate source. It is the projection of pointA on the closest way.
    # the nearest node of the nearest way could be dozens of meters away
    # in either direction so it would be impractical to use it
    _min = 10
    for way in list(ways.values()):
        for i in range(1, len(way['nodes'])):
            node1Id = way['nodes'][i-1]
            node2Id = way['nodes'][i]
            node1 = nodes[node1Id]
            node2 = nodes[node2Id]
            projection = get_projection_on_segment(pointA, [node1, node2])
            d = get_flying_distance(projection, pointA)
            if d < _min:
                _min = d
                _argmin = projection
                _argmin['neighbors'] = [
                    {'distance': get_flying_distance(projection, node1), 'node': node1, 'way': way['id']},
                    {'distance': get_flying_distance(projection, node2), 'node': node2, 'way': way['id']}
                ]
    source = _argmin
    source['isSource'] = True
    source['id'] = 0
    print('found source at distance ' + str(_min))
    nodes[0] = source

    # locate target
    _min = 10
    for node in list(nodes.values()):
        d = get_flying_distance(node, pointB)
        if d < _min:
            _min = d
            _argmin = node
    _argmin['isTarget'] = True
     
    return source

def get_way_name(way):
    return way['tags']['name'] if 'name' in way['tags'] else way['tags']['highway']

def have_same_name(way1, way2):
    return get_way_name(way1) == get_way_name(way2)

def should_write_line(previous_way, next_way, node, nodes):
    previous_name = get_way_name(previous_way)
    next_name = get_way_name(next_way)
    write_line = previous_name != next_name
    if write_line:
        if get_way_name(previous_way) not in constants.DIFFICULT_WAYS:
            bearing_before = get_bearing_at_node(previous_way, node, nodes)
            bearing_after = get_bearing_at_node(next_way, node, nodes)
            write_line = bearing_before is None or bearing_after is None \
                or abs(bearing_after - bearing_before) > constants.PARALLELISM_TOLERANCE
    return write_line

def mark_next_point(nodes, ways, prioque, markings):
    marking = prioque.get().item
    mark_id = str(marking.node_id) + '-' + str(marking.preceding_way) if marking.preceding_way is not None else str(marking.node_id)
    if mark_id in markings:
        return None

    node = nodes[marking.node_id]
    for link in node['neighbors']:
        # no going backwards to node of previous mark
        if marking.preceding_marking and link['node']['id'] == marking.preceding_marking.node_id:
            continue
        new_sms_character_count = marking.sms_character_count
        if marking.preceding_way and should_write_line(ways[marking.preceding_way], ways[link['way']], node, nodes):
            new_sms_character_count += constants.ITINERARY_BASE_DIRECTION_CHARACTER_COUNT
            new_sms_character_count += min(
                constants.MAX_CHARS_PER_WAY,
                len(get_way_name(ways[marking.preceding_way])))
        new_distance = marking.distance_from_A + link['distance']
        score = get_score(new_distance, new_sms_character_count)
        new_marking = Marking(link['node']['id'], new_distance, new_sms_character_count, marking, link['way'])
        prioque.put(PrioritizedItem(score, new_marking))

    markings[mark_id] = marking
    return marking

def get_node_path(marking, nodes):
    path = []
    current_node = nodes[marking.node_id]
    i = 0
    current_marking = marking
    while current_node and 'isSource' not in current_node and i < 1000:
        if current_marking.preceding_marking is None:
            break
        current_node = nodes[current_marking.preceding_marking.node_id]
        current_marking = current_marking.preceding_marking
        path.append(current_node)
        i+=1 
    if i == 1000:
        print('big trouble')
    if 'isSource' not in current_node:
        print('where is source ?')
    #print([x['id'] for x in path])
    print(f'path has length {len(path)}')
    return path[::-1]

def get_actual_directions(path, ways, nodes, pointA):
    directions = []
    previous_node = pointA
    previous_way = None
    for i in range(1, len(path)):
        node1 = path[i-1]
        node2 = path[i]
        link = [n for n in node1['neighbors'] if n['node']['id'] == node2['id']][0]
        way = ways[link['way']]
        name = get_way_name(way)
        if len(directions) == 0 or (previous_way is not None and should_write_line(previous_way, way, node1, nodes)):
            angle = get_angle(previous_node, node1, node2)
            angle = (360 - angle) % 360
            angle -= 180
            directions.append({'way': name, 'angle': angle ,'distance': get_flying_distance(node1, node1)})
        else:
            directions[-1]['distance'] += get_flying_distance(node1, node2)
        previous_node = node1
        previous_way = way
    return directions

def dijkstra(map_data, pointA, pointB):
    elements = map_data['elements']
    print('nb of elements is ' + str(len(elements)))
    nodes = {x['id']: x for x in elements if x['type'] == 'node'}
    print('nb of nodes is ' + str(len(nodes)))
    ways = {x['id']: x for x in elements if x['type'] == 'way'}
    print('nb of ways is ' + str(len(ways)))
    source = compute_neighbors(nodes, ways, pointA, pointB)
    pointA['isSource'] = True
    markings = {}
    prioque = PriorityQueue()
    first_marking = Marking(source['id'], 0, constants.ITINERARY_DISTANCE_CHARACTER_COUNT, None, None)
    prioque.put(PrioritizedItem(0, first_marking))
    while not prioque.empty():
        marking = mark_next_point(nodes, ways, prioque, markings)
        if marking and marking.node_id and 'isTarget' in nodes[marking.node_id]:
            print('path was found')
            distance = marking.distance_from_A
            print(distance)
            print(marking.sms_character_count, ' characters')
            print(get_required_sms_number(marking.sms_character_count), ' is the required number of sms')
            path = get_node_path(marking, nodes)
            return {
                'distance': distance,
                'directions': get_actual_directions(path, ways, nodes, pointA)
            }
    print('Path not found')
    return {'distance': 0, 'directions': []}
