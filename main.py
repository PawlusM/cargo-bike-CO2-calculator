import csv

from scripts.cbsim import OSM_download, net, net_draw, node, stochastic, common, vehicles, CVRP
from datetime import datetime
from pathlib import Path
import os

N = net.Net()

N.bbox = net.AreaBoundingBox(longitude_west=19.9300, longitude_east=19.94537, latitude_south=50.05395,
                             latitude_north=50.06631)

N = OSM_download.generate_network(net=N, simplify=True, simplify_tolerance=10, draw_network=False)

N.sdm = N.floyd_warshall(N.nodes)

max_index = len(N.nodes) - 1

# TODO add business downloader
with open("data/rynek_nodes.txt") as file:
    for line in file:
        data = line.split('\t')
        max_index = max_index + 1
        new_node = node.Node(nid=max_index, name=data[1])
        new_node.type = data[2]
        new_node.y = float(data[3])
        new_node.x = float(data[4])
        N.nodes.append(new_node)
#  File read will be removed when the business downloader is complete
N.set_closest_itsc()

# TODO add better probs weights and dimensions, pack this into another file
probs = {'R': 0.3, 'H': 0.1, 'S': 0.4, 'P': 0.15, 'W': 0.05, "B": 0.3, "K": 0.1, "Ks": 0.1, 'N': 0, 'L': 0}

weightLaw = 0  # 0 - rectangular, 1 - normal, 2 - exponential
weightLocation = 0  # grams
weightScale = 20000

dimensionsLaw = 0
dimensionsLocation = 0  # mm
dimensionsScale = 400

s_weight = stochastic.Stochastic(law=weightLaw, location=weightLocation, scale=weightScale)
s_dimensions = stochastic.Stochastic(law=dimensionsLaw, location=dimensionsLocation, scale=dimensionsScale)

lpoints = [node for node in N.nodes if node.type == 'L']
sender = lpoints[0]

N.gen_requests(sender=lpoints[0], nodes=N.nodes, probs=probs, s_weight=s_weight, s_dimensions=s_dimensions)
print("bike:")
N.vehicles = vehicles.Vehicles(common.load_dict_from_json("data/data_model_bike.json"))
bike_routes, bike_distances = CVRP.solve(N, timeout=100)
bike_total_distances = CVRP.calculate_total_distances(bike_distances)
print(f"best bike distance: {min(bike_total_distances)}\n")

print("van:")
N.vehicles = vehicles.Vehicles(common.load_dict_from_json("data/data_model_van.json"))
van_routes, van_distances = CVRP.solve(N, timeout=100)
van_total_distances = CVRP.calculate_total_distances(van_distances)
print(f"best van distance: {min(van_total_distances)}\n")

folder_name = f"{N.bbox.__str__().replace(',','_').strip('()')}_{weightLaw}_law_{weightLocation}_location_{weightScale}_scale_{dimensionsLaw}_dimLaw_{dimensionsLocation}_dimLoc{dimensionsScale}_dimScale"
folder_path = 'results/CVRP/' + folder_name
absolute_folder_path = os.getcwd() + '/' + folder_path
Path(absolute_folder_path).mkdir(parents=True, exist_ok=True)

now = datetime.now()
dtString = now.strftime("%Y_%m_%d_%H_%M_%S")


results_path = absolute_folder_path + '/' + "results.csv"
if not(os.path.isfile(results_path)):
    with open(results_path, 'w') as f:
        f.write("datetime,bike_count,bike_total_distance,van_count,van_total_distance\n")

with open(results_path,'a') as f:
    f.write(f"{dtString};{len(bike_routes[0])};{min(bike_total_distances)};{len(van_routes[0])};{min(van_total_distances)}\n")

common_path = absolute_folder_path + '/' + dtString
common.save_results(common_path + "_net.pkl", N)
common.save_results(common_path + "_bike_routes.pkl", bike_routes)
common.save_results(common_path + "_van_routes.pkl", van_routes)



net_draw.draw_results(N)
pass
