import time

from scripts.cbsim import OSM_download, net, net_draw, node, stochastic, common, vehicles, CVRP, get_OSMbusinesses
from datetime import datetime
from pathlib import Path
import multiprocessing as mp
import os


def listener(q):
    counter = 0
    while True:
        message = q.get()

        # print(f"got: {message}")
        if message == "kill":
            print("kill")
            break
        counter += 1
        N, bike_routes, bike_distances, min_bike_distance, van_routes, van_distances, min_van_distance = message

        now = datetime.now()
        dtString = now.strftime("%Y_%m_%d_%H_%M_%S_%s")

        results_path = absolute_folder_path + '/' + "results.csv"
        if not (os.path.isfile(results_path)):
            with open(results_path, 'w') as f:
                f.write("datetime;bike_count;bike_total_distance;van_count;van_total_distance\n")

        with open(results_path, 'a') as f:
            f.write(
                f"{dtString};{len(bike_routes[0])};{min_bike_distance};{len(van_routes[0])};{min_van_distance}\n")

        common_path = absolute_folder_path + '/' + dtString + f"thread_{N.thread}"
        common.save_results(common_path + "_net.pkl", N)
        common.save_results(common_path + "_bike_routes.pkl", bike_routes)
        common.save_results(common_path + "_van_routes.pkl", van_routes)


def experiment(N, thread, q, experiment_count):
    N.thread = thread

    for interator in range(experiment_count):
        N.demand = []
        N.gen_requests(sender=lpoints[0], nodes=N.nodes, probs=probs, s_weight=s_weight, s_dimensions=s_dimensions)
        print(f"T{thread}: bike:")
        min_bike_distance = -1

        N.vehicles = N.bikes
        while min_bike_distance == -1:
            bike_routes, bike_distances, N = CVRP.solve(N, timeout=100)
            bike_total_distances = CVRP.calculate_total_distances(bike_distances)
            try:
                min_bike_distance = min(bike_total_distances)
            except ValueError:
                min_bike_distance = -1
                N.vehicles.count = N.vehicles.count + 1
                print(f"T{thread}: adding bike {N.vehicles.count}")

        print(f"T{thread}: best total bike distance: {min_bike_distance}\n")

        print(f"T{thread}: van:")
        min_van_distance = -1
        N.vehicles = N.vans
        while min_van_distance == -1:
            van_routes, van_distances, N = CVRP.solve(N, timeout=100)
            van_total_distances = CVRP.calculate_total_distances(van_distances)

            try:
                min_van_distance = min(van_total_distances)
            except ValueError:
                min_van_distance = -1
                N.vehicles.count = N.vehicles.count + 1
                print(f"T{thread}: adding van {N.vehicles.count}")

        print(f"T{thread}: best total van distance: {min_van_distance}\n")
        result = N, bike_routes, bike_distances, min_bike_distance, van_routes, van_distances, min_van_distance
        q.put(result)


if __name__ == "__main__":

    N = net.Net()

    N.bbox = net.AreaBoundingBox(longitude_west=19.93000, longitude_east=19.94537, latitude_south=50.05395,
                                 latitude_north=50.06631)

    N = OSM_download.generate_network(net=N, simplify=True, simplify_tolerance=10, draw_network=False)

    load_point = node.Node(nid=0, name="Load Point")
    load_point.x = 19.9391056
    load_point.y = 50.06626309999999
    load_point.type = 'L'

    N.nodes.append(load_point)

    N.sdm = N.floyd_warshall(N.nodes)  # sdm with intersection only

    file_path = "data/temp_nodes.csv"

    get_OSMbusinesses.get_clients([N.polygon.create_osm_area()], file_path)
    businesses = common.load_csv(file_path)

    max_index = len(N.nodes) - 1

    for business in businesses:
        assert len(business) == 11

        if business['NAME'] == '':  # there are some empty businesses
            continue

        max_index = max_index + 1
        new_node = node.Node(nid=max_index, name=business['NAME'])

        for type in [business['AMENITY'], business['SHOP'], business['TOURISM'], business['OFFICE']]:
            if type == "":
                continue
            if type in get_OSMbusinesses.L_B:
                new_node.type = 'L_B'
                break
            elif type in get_OSMbusinesses.F_D:
                new_node.type = 'F_D'
                break
            elif type in get_OSMbusinesses.C_S:
                new_node.type = 'C_S'
                break
            elif type in get_OSMbusinesses.O_S:
                new_node.type = 'O_S'
                break
            elif type in get_OSMbusinesses.O:
                new_node.type = 'O'
                break
            else:
                new_node.type = 'V_S'

        new_node.y = float(business['X'])
        new_node.x = float(business['Y'])
        N.nodes.append(new_node)


    N.set_closest_itsc()

    # net_draw.draw_results(N)

    # TODO add better probs weights and dimensions, pack this into another file
    probs = {'F_D': 0.3, 'L_B': 0.1, 'C_S': 0.4, 'V_S': 0.15, 'O_S': 0.05, 'O': 0.05, 'N': 0, 'L': 0}

    weightLaw = 0  # 0 - rectangular, 1 - normal, 2 - exponential
    weightLocation = 0  # grams
    weightScale = 25000  # 25kg for UPS, InPost, 31,5 kg for for DPD, DHL

    dimensionsLaw = 0
    dimensionsLocation = 0  # mm
    dimensionsScale = 400

    experiment_per_thread = 10

    s_weight = stochastic.Stochastic(law=weightLaw, location=weightLocation, scale=weightScale)
    s_dimensions = stochastic.Stochastic(law=dimensionsLaw, location=dimensionsLocation, scale=dimensionsScale)

    lpoints = [node for node in N.nodes if node.type == 'L']
    sender = lpoints[0]

    N.vans = vehicles.Vehicles(common.load_dict_from_json("data/data_model_van.json"))
    N.bikes = vehicles.Vehicles(common.load_dict_from_json("data/data_model_bike.json"))

    folder_name = f"{N.bbox.__str__().replace(',', '_').strip('()')}_{weightLaw}_law_{weightLocation}_location_{weightScale}_scale_{dimensionsLaw}_dimLaw_{dimensionsLocation}_dimLoc{dimensionsScale}_dimScale"
    folder_path = 'results/CVRP/' + folder_name
    absolute_folder_path = os.getcwd() + '/' + folder_path
    Path(absolute_folder_path).mkdir(parents=True, exist_ok=True)

    manager = mp.Manager()
    q = manager.Queue()

    pool = mp.Pool(mp.cpu_count() + 2)

    watcher = pool.apply_async(listener, (q,))

    jobs = []
    for i in range(mp.cpu_count()):
        job = pool.apply_async(experiment, args=(N, i, q, experiment_per_thread))
        jobs.append(job)

    for job in jobs:
        job.get()

    q.put("kill")
    pool.close()
    pool.join()
