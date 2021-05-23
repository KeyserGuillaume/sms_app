from queue import PriorityQueue
from geometry_utils import get_flying_distance, get_projection_on_segment, get_angle

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
    
    # locate source
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

    # locate target
    _min = 10
    for node in list(nodes.values()):
        d = get_flying_distance(node, pointB)
        if d < _min:
            _min = d
            _argmin = node
    _argmin['isTarget'] = True
     
    return source

def have_same_name(way1, way2):
    name1 = way1['tags']['name'] if 'name' in way1['tags'] else way1['tags']['highway'] 
    name2 = way2['tags']['name'] if 'name' in way2['tags'] else way2['tags']['highway']
    return name1 == name2

def mark_next_point(ways, prioque, markings):
    distanceToA, node, predecessor, preceding_way = prioque.get()
    if node['id'] in markings:
        return None
    # print(distanceToA)
    node['distance'] = distanceToA
    node['predecessor'] = predecessor
    node['preceding_way'] = preceding_way
    directions_count = predecessor['directions_count'] if predecessor else 0
    if preceding_way and predecessor and predecessor['preceding_way']\
       and not have_same_name(ways[preceding_way], ways[predecessor['preceding_way']]):
        directions_count += 1
    node['directions_count'] = directions_count

    for link in node['neighbors']:
        if predecessor and link['node']['id'] == predecessor['id']:
            continue
        directions_count = node['directions_count']
        if preceding_way and not have_same_name(ways[preceding_way], ways[link['way']]):
            directions_count += 1
        prioque.put((distanceToA + link['distance'], link['node'], node, link['way']))

    markings[node['id']] = True
    return node

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

def get_actual_directions(path, ways, pointA):
    directions = []
    previous_node = pointA
    for i in range(1, len(path)):
        node1 = path[i-1]
        node2 = path[i]
        link = [n for n in node1['neighbors'] if n['node']['id'] == node2['id']][0]
        way = ways[link['way']]
        name = way['tags']['name'] if 'name' in way['tags'] else way['tags']['highway']
        if len(directions) == 0 or directions[-1]['way'] != name:
            angle = get_angle(previous_node, node1, node2)
            angle = (360 - angle) % 360
            angle -= 180
            directions.append({'way': name, 'angle': angle ,'distance': link['distance']})
        else:
            directions[-1]['distance'] += link['distance']
        previous_node = node1
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
    prioque.put((0, source, None, None))
    while not prioque.empty():
        node = mark_next_point(ways, prioque, markings)
        if node and 'isTarget' in node:
            print('path was found')
            distance = node['distance']
            print(distance)
            print(node['directions_count'])
            path = get_node_path(node)
            return {
                'distance': distance,
                'directions': get_actual_directions(path, ways, pointA)
            }
    print('Path not found')
    return {'distance': 0, 'directions': []}
