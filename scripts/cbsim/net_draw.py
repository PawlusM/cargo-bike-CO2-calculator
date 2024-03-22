import webbrowser, folium, numpy as np, geopandas as gpd
import json, pyautogui
from folium.plugins import Geocoder
from http.server import BaseHTTPRequestHandler, HTTPServer

from scripts.cbsim.net import AreaBoundingBox, AreaBoundingPolygon
from scripts.cbsim.node import Node

from shapely.geometry.polygon import Polygon


folium_port = 3001
coordinates = []
listen_for_multiple = False
file_name = './results/test_map.html'


def find_popup_slice(html):
    '''
    Find the starting and ending index of popup function
    '''

    pattern = "function latLngPop(e)"

    # starting index
    starting_index = html.find(pattern)

    #
    tmp_html = html[starting_index:]

    #
    found = 0
    index = 0
    opening_found = False
    while not opening_found or found > 0:
        if tmp_html[index] == "{":
            found += 1
            opening_found = True
        elif tmp_html[index] == "}":
            found -= 1

        index += 1

    # determine the ending index of popup function
    ending_index = starting_index + index

    return starting_index, ending_index


def find_variable_name(html, name_start):
    variable_pattern = "var "
    pattern = variable_pattern + name_start

    starting_index = html.find(pattern) + len(variable_pattern)
    tmp_html = html[starting_index:]
    ending_index = tmp_html.find(" =") + starting_index

    return html[starting_index:ending_index]


def custom_code(popup_variable_name, map_variable_name, folium_port):
    return '''
            // custom code
            function latLngPop(e) {
                %s
                    .setLatLng(e.latlng)
                    .setContent(`
                        lat: ${e.latlng.lat}, lng: ${e.latlng.lng}
                        <button onClick="
                            fetch('http://localhost:%s', {
                                method: 'POST',
                                mode: 'no-cors',
                                headers: {
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    latitude: ${e.latlng.lat},
                                    longitude: ${e.latlng.lng}
                                })
                            });

                            L.marker(
                                [${e.latlng.lat}, ${e.latlng.lng}],
                                {}
                            ).addTo(%s);
                        "> Save coordinates </button>
                        <button onClick="
                            fetch('http://localhost:%s', {
                                method: 'POST',
                                mode: 'no-cors',
                                headers: {
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                },
                                body: 'q'
                            });
                        "> Quit </button>
                    `)
                    .openOn(%s);
            }
            // end custom code
    ''' % (popup_variable_name, folium_port, map_variable_name, folium_port, map_variable_name)


def create_map(bbox):
    bbox_polygon = Polygon(np.array([
        [bbox.longitude_east, bbox.latitude_south],
        [bbox.longitude_east, bbox.latitude_north],
        [bbox.longitude_west, bbox.latitude_north],
        [bbox.longitude_west, bbox.latitude_south]
    ]))

    map = folium.Map(location=[0.5 * (bbox.latitude_south + bbox.latitude_north),
                               0.5 * (bbox.longitude_east + bbox.longitude_west)], zoom_start=15,
                     tiles="CartoDB Positron")
    return map


def draw_bounding_polygon(map, polygon):
    folium.GeoJson(data=gpd.GeoSeries(polygon).to_json(),
                   style_function=lambda x: {'fillColor': 'red'}, name="Bounding polygon").add_to(map)
    return map


def draw_nodes_and_links(map, nodes, links):
    nodes_group = folium.FeatureGroup("Nodes").add_to(map)

    businesses_group = folium.FeatureGroup("Businesses").add_to(map)

    for single_node in nodes:
        if single_node.type == "N":
            folium.Circle(
                radius=5,
                location=[single_node.y, single_node.x],
                tooltip=single_node.name,
                popup=f"{single_node.name},\nX:{single_node.x}\nY:{single_node.y}\nnid:{single_node.nid}",
                color="green",
                fillColor="green"
            ).add_to(nodes_group)
        elif single_node.type == "L":
            folium.Marker(
                location=[single_node.y, single_node.x],
                tooltip=single_node.name,
                popup=f"{single_node.name},\nX:{single_node.x}\nY:{single_node.y}\nnid:{single_node.nid}",
                color="red",
                fillColor="red",
                draggable=False
            ).add_to(nodes_group)

        else:
            folium.Circle(
                radius=3,
                location=[single_node.y, single_node.x],
                tooltip=single_node.name,
                popup=f"{single_node.name},\nType:{single_node.type}\nX:{single_node.x}\nY:{single_node.y}\n ITSC:{single_node.closest_itsc.name}\nnid:{single_node.nid}",
                color="blue",
                fillColor="blue"
            ).add_to(businesses_group)

    links_group = folium.FeatureGroup("Links").add_to(map)
    for single_link in links:
        folium.PolyLine(
            [(single_link.in_node.y, single_link.in_node.x), (single_link.out_node.y, single_link.out_node.x)],
            tooltip=f"{single_link.in_node.name} -> {single_link.out_node.name}",
            popup=f"Y:{single_link.in_node.y}\nX:{single_link.in_node.x}\nlen:{round(single_link.weight, 4)}").add_to(
            links_group)

    folium.LayerControl().add_to(map)

    return map


def refresh():
    # very ugly workaround in order not to open a lot of tabs
    # it can be solved using selenium, but then the user would have to download external packages outside PIP
    pyautogui.hotkey('f5')


def close_tab():
    with pyautogui.hold('ctrl'):
        pyautogui.hotkey('w')


class FoliumServer(BaseHTTPRequestHandler):

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        kill = False
        data = post_data.decode("utf-8")
        if data.lower() == 'q':
            kill = True
        elif 'latitude' in data:
            coordinates.append(json.loads(data))
            if not listen_for_multiple:
                kill = True

        if kill:
            raise KeyboardInterrupt("Intended exception to exit webserver")

        self._set_response()


def listen_to_folium_map(port=3001):
    server_address = ('', port)
    httpd = HTTPServer(server_address, FoliumServer)
    print("Server started")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    print("Server stopped...")


def select_points(map):
    map.save(file_name)

    # reading the folium file
    html = None
    with open(file_name, 'r') as mapfile:
        html = mapfile.read()

    # find variable names
    map_variable_name = find_variable_name(html, "map_")
    popup_variable_name = find_variable_name(html, "lat_lng_popup_")

    # determine popup function indicies
    pstart, pend = find_popup_slice(html)

    # inject code
    with open(file_name, 'w') as mapfile:
        mapfile.write(
            html[:pstart] + \
            custom_code(popup_variable_name, map_variable_name, folium_port) + \
            html[pend:]
        )

    webbrowser.open(file_name, new=0)

    listen_to_folium_map(folium_port)
    if coordinates is not []:
        return coordinates


def select_loading_point(net):
    m = create_map(net.bbox)
    m = draw_bounding_polygon(m, net.polygon.geometry)
    m = draw_nodes_and_links(m, net.nodes, net.links)

    folium.LatLngPopup().add_to(m)

    map_title = "Select the loading point location.\n Press save to select a point and continue"
    title_html = f'<h1 style="position:absolute;z-index:100000;left:40vw" >{map_title}</h1>'
    m.get_root().html.add_child(folium.Element(title_html))

    global listen_for_multiple
    listen_for_multiple = False

    global coordinates
    coordinates = []

    results = select_points(m)
    close_tab()

    assert len(results) == 1

    if results[0] is not []:
        load_point = Node(nid=net.nodes[-1].nid + 1, name="Load Point")
        load_point.x = coordinates[0]['longitude']
        load_point.y = coordinates[0]['latitude']
        load_point.type = 'L'
        net.nodes.append(load_point)
        draw_results(net)

        refresh()

    net.set_closest_itsc()

    return net

    # # reading the folium file
    # html = None
    # with open(file_name, 'r') as mapfile:
    #     html = mapfile.read()
    #
    # # find variable names
    # map_variable_name = find_variable_name(html, "map_")
    # popup_variable_name = find_variable_name(html, "lat_lng_popup_")
    #
    # # determine popup function indicies
    # pstart, pend = find_popup_slice(html)
    #
    # # inject code
    # with open(file_name, 'w') as mapfile:
    #     mapfile.write(
    #         html[:pstart] + \
    #         custom_code(popup_variable_name, map_variable_name, folium_port) + \
    #         html[pend:]
    #     )
    #
    # webbrowser.open(file_name, new=0)

    listen_to_folium_map(folium_port)
    if coordinates is not []:
        load_point = Node(nid=net.nodes[-1].nid + 1, name="Load Point")
        load_point.x = coordinates[0]['longitude']
        load_point.y = coordinates[0]['latitude']
        load_point.type = 'L'
        net.nodes.append(load_point)
        draw_results(net)

        refresh()

        coordinates.clear()

    return m, net


def draw(map):
    map.save(file_name)
    webbrowser.open(file_name, new=0)


def create_bounding_polygon(net):
    default_bbox = AreaBoundingBox(longitude_west=19.93000, longitude_east=19.94537, latitude_south=50.05395,
                                   latitude_north=50.06631)
    default_map = create_map(bbox=default_bbox)

    folium.LatLngPopup().add_to(default_map)
    Geocoder().add_to(default_map)

    map_title = "Select the bounding polygon.\n Press save to save one point, press quit to finish."
    title_html = f'<h1 style="position:absolute;z-index:100000;left:40vw" >{map_title}</h1>'
    default_map.get_root().html.add_child(folium.Element(title_html))
    global listen_for_multiple
    listen_for_multiple = True

    global coordinates
    coordinates = []

    results = select_points(default_map)
    close_tab()

    polygon_points = []

    for point in results:
        to_append = (point['longitude'], point['latitude'])
        polygon_points.append(to_append)

    polygon_html = tuple(polygon_points)

    polygon = AreaBoundingPolygon(polygon_points)
    draw_bounding_polygon(default_map, polygon.geometry)
    net.polygon = polygon
    return net


def draw_results(net):
    m = create_map(bbox=net.bbox)

    m = draw_bounding_polygon(m, net.polygon.geometry)

    m = draw_nodes_and_links(m, nodes=net.nodes, links=net.links)

    draw(m)
