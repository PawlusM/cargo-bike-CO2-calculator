from scripts.cbsim import OSM_download, net, net_draw, node

N = net.Net()

N.bbox = net.AreaBoundingBox(longitude_west=19.9300, longitude_east=19.94537, latitude_south=50.05395,
                             latitude_north=50.06631)

N = OSM_download.generate_network(net=N, simplify=True, simplify_tolerance=10, draw_network=False)

max_index = len(N.nodes) - 1

# will be removed when the business downloader is complete
with open("data/rynek_nodes.txt") as file:
    for line in file:
        data = line.split('\t')
        max_index = max_index + 1
        new_node = node.Node(nid=max_index,name=data[1])
        new_node.type = data[2]
        new_node.y = float(data[3])
        new_node.x = float(data[4])
        N.nodes.append(new_node)


N.set_closest_itsc()

net_draw.draw_results(N)
