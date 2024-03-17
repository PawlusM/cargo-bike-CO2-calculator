import networkx
import networkx as nx
import osmnx as ox
import shapely

from scripts.cbsim.node import Node
from scripts.cbsim.net import AreaBoundingPolygon, AreaBoundingBox

ox.settings.use_cache = True


def generate_network(net, type: str = "bike", draw_network: bool = False, simplify: bool = False,
                     simplify_tolerance: int = 15):
    assert (net.bbox is not None) or (net.polygon is not None), "No location given"

    if net.polygon is None and net.bbox is not None:  # convert bbox to polygon
        points = net.bbox.convert_to_polygon_points()
        net.polygon = AreaBoundingPolygon(points)

    if net.bbox is None:
        lon_min, lon_max = net.polygon.points[0][0]
        lat_max, lat_min = net.polygon.points[0][1]
        for point in net.polygon.points:
            if point[0] < lon_min:
                lon_min = point[0]
            if point[0] > lon_max:
                lon_max = point[0]
            if point[1] < lat_min:
                lat_min = point[1]
            if point[1] > lat_max:
                lat_max = point[1]

        net.bbox = AreaBoundingBox(longitude_west=lon_min, longitude_east=lon_max, latitude_south=lat_min,
                                   latitude_north=lat_max)

    G = ox.graph_from_polygon(net.polygon.geometry, network_type=type, truncate_by_edge=False)

    # impute edge (driving) speeds and calculate edge travel times
    G = ox.speed.add_edge_speeds(G)
    G = ox.speed.add_edge_travel_times(G)

    node_count = len(G)

    if simplify:
        G_proj = ox.project_graph(G)

        G_proj = ox.consolidate_intersections(G_proj, tolerance=simplify_tolerance, rebuild_graph=True, dead_ends=True,
                                              reconnect_edges=True)
        ox.project_graph(G_proj, to_latlong=True)

        print(f"Simplified {node_count - len(G_proj)} nodes.")

        nodes = ox.graph_to_gdfs(G_proj, edges=False).to_crs("epsg:4326")

        for single_node_index in nodes.index:
            new_node = Node(nid=single_node_index, name=f"ITSC{str(nodes.osmid_original[single_node_index])}")
            if nodes.lon[single_node_index] is float and nodes.lat[
                single_node_index] is float:  # node was not simplified
                new_node.x = nodes.lon[single_node_index]
                new_node.y = nodes.lat[single_node_index]
            else:  # node was simplified so no explicit coordinates, take centroid instead, this gives warning but the results seems to be ok
                new_node.x = nodes.centroid.x[single_node_index]
                new_node.y = nodes.centroid.y[single_node_index]

            new_node.type = 'N'
            net.nodes.append(new_node)

        links_dict = dict(G_proj.edges)

        for single_link_index in links_dict.keys():
            net.add_link(in_id=single_link_index[0], out_id=single_link_index[1],
                         weight=links_dict[single_link_index]['length'] / 1000)

    else:

        nodes_dict = dict(G.nodes)
        links_dict = dict(G.edges)

        # populate Net from gathered data
        for single_node in nodes_dict.keys():
            new_node = Node(nid=int(single_node), name=f"ITSC{single_node}")
            new_node.x = nodes_dict[single_node]['x']
            new_node.y = nodes_dict[single_node]['y']
            new_node.type = 'N'
            net.nodes.append(new_node)

        for single_link in links_dict.keys():
            net.add_link(in_id=single_link[0], out_id=single_link[1],
                         weight=float(links_dict[single_link]['length']) / 1000,  # not a fan of kilometers here
                         directed=links_dict[single_link]['oneway'])

    if draw_network:
        draw(G)

    return net


def draw(graph: networkx.Graph):
    # you can convert MultiDiGraph to/from GeoPandas GeoDataFrames
    gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(graph)
    G = ox.utils_graph.graph_from_gdfs(gdf_nodes, gdf_edges, graph_attrs=graph.graph)

    # convert MultiDiGraph to DiGraph to use nx.betweenness_centrality function
    # choose between parallel edges by minimizing travel_time attribute value
    D = ox.utils_graph.get_digraph(G, weight="travel_time")

    # calculate node betweenness centrality, weighted by travel time
    bc = nx.betweenness_centrality(D, weight="travel_time", normalized=True)
    nx.set_node_attributes(G, values=bc, name="bc")

    # plot the graph, coloring nodes by betweenness centrality
    nc = ox.plot.get_node_colors_by_attr(G, "bc", cmap="plasma")
    fig, ax = ox.plot.plot_graph(
        G, bgcolor="k", node_color=nc, node_size=50, edge_linewidth=2, edge_color="#333333"
    )

    # save graph as a geopackage or graphml file
    ox.io.save_graph_geopackage(G, filepath="results/graph.gpkg")
    ox.io.save_graphml(G, filepath="results/graph.graphml")
