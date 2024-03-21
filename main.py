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
            van_routes, van_distances, N = CVRP.solve(N, timeout=200)
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

    n = net.Net()

    # n.bbox = net.AreaBoundingBox(longitude_west=19.93000, longitude_east=19.94537, latitude_south=50.05395,
    #                              latitude_north=50.06631)

    boundaries_krakow = (
        (19.9361, 50.0661), (19.9419, 50.0655), (19.9447, 50.0644), (19.9436, 50.0609), (19.9406, 50.0587),
        (19.9389, 50.0546), (19.9375, 50.0555), (19.9352, 50.0557), (19.9334, 50.0589), (19.9319, 50.0619))

    n.polygon = net.AreaBoundingPolygon(boundaries_krakow)

    n = OSM_download.generate_network_and_businesses(n)


    net_draw.draw_results(n)

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

    lpoints = [node for node in n.nodes if node.type == 'L']
    sender = lpoints[0]

    n.vans = vehicles.Vehicles(common.load_dict_from_json("data/data_model_van.json"))
    n.bikes = vehicles.Vehicles(common.load_dict_from_json("data/data_model_bike.json"))

    folder_name = f"{n.bbox.__str__().replace(',', '_').strip('()')}_{weightLaw}_law_{weightLocation}_location_{weightScale}_scale_{dimensionsLaw}_dimLaw_{dimensionsLocation}_dimLoc{dimensionsScale}_dimScale"
    folder_path = 'results/CVRP/' + folder_name
    absolute_folder_path = os.getcwd() + '/' + folder_path
    Path(absolute_folder_path).mkdir(parents=True, exist_ok=True)

    manager = mp.Manager()
    q = manager.Queue()

    pool = mp.Pool(mp.cpu_count() + 2)

    watcher = pool.apply_async(listener, (q,))

    jobs = []
    for i in range(mp.cpu_count()):
        job = pool.apply_async(experiment, args=(n, i, q, experiment_per_thread))
        jobs.append(job)

    for job in jobs:
        job.get()

    q.put("kill")
    pool.close()
    pool.join()
