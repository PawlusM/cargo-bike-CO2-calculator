import webbrowser, folium, numpy as np, geopandas as gpd
from shapely.geometry.polygon import Polygon


def draw_results(net):
    bbox_polygon = Polygon(np.array([
        [net.bbox.longitude_east, net.bbox.latitude_south],
        [net.bbox.longitude_east, net.bbox.latitude_north],
        [net.bbox.longitude_west, net.bbox.latitude_north],
        [net.bbox.longitude_west, net.bbox.latitude_south]
    ]))

    m = folium.Map(location=[0.5 * (net.bbox.latitude_south + net.bbox.latitude_north),
                             0.5 * (net.bbox.longitude_east + net.bbox.longitude_west)], zoom_start=15,
                   tiles="CartoDB Positron")

    folium.GeoJson(data=gpd.GeoSeries(bbox_polygon).to_json(),
                   style_function=lambda x: {'fillColor': 'red'}, name="Bounding box").add_to(m)

    nodes_group = folium.FeatureGroup("Nodes").add_to(m)

    for single_node in net.nodes:
        if single_node.type == "N":
            folium.Circle(
                radius=5,
                location=[single_node.y, single_node.x],
                tooltip=single_node.name,
                popup=f"{single_node.name},\nX:{single_node.x}\nY:{single_node.y}",
                color="green",
                fillColor="green"

            ).add_to(nodes_group)

    links_group = folium.FeatureGroup("Links").add_to(m)

    for single_link in net.links:
        folium.PolyLine(
            [(single_link.in_node.y, single_link.in_node.x), (single_link.out_node.y, single_link.out_node.x)],
            tooltip=f"{single_link.in_node.name} -> {single_link.out_node.name}",
            popup=f"Y:{single_link.in_node.y}\nX:{single_link.in_node.x}\nlen:{round(single_link.weight, 4)}").add_to(
            links_group)

    folium.LayerControl().add_to(m)
    file_name = './results/test_map.html'
    m.save(file_name)
    webbrowser.open(file_name)
