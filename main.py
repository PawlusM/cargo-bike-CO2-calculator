import time

from scripts.cbsim import OSM_download, net, net_draw, node, stochastic, common, vehicles, CVRP, co2
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
        N, bike_routes, bike_distances, min_bike_distance, bike_count, van_routes, van_distances, min_van_distance, van_count, van_emissions = message

        now = datetime.now()
        dtString = now.strftime("%Y_%m_%d_%H_%M_%S_%s")

        results_path = absolute_folder_path + '/' + "results.csv"
        if not (os.path.isfile(results_path)):
            with open(results_path, 'w') as f:
                f.write("datetime;thread;bike_count;bike_total_distance;van_count;van_total_distance;van_emissions\n")

        with open(results_path, 'a') as f:
            f.write(
                f"{dtString};{N.thread};{bike_count};{min_bike_distance};{van_count};{min_van_distance};{van_emissions}\n")

        common_path = absolute_folder_path + '/' + dtString + f"thread_{N.thread}"
        common.save_results(common_path + "_net.pkl", N)
        common.save_results(common_path + "_bike_routes.pkl", bike_routes)
        common.save_results(common_path + "_van_routes.pkl", van_routes)


def experiment(N, thread, q, experiment_count, timeout):
    N.thread = thread

    for interator in range(experiment_count):
        N.demand = []
        N.gen_requests(sender=lpoints[0], nodes=N.nodes, probs=probs, s_weight=s_weight, s_dimensions=s_dimensions)
        print(f"T{thread}: bike:")
        min_bike_distance = -1

        N.vehicles = N.bikes
        while min_bike_distance == -1:
            bike_routes, bike_distances, N = CVRP.solve(N, timeout=timeout)
            bike_total_distances = CVRP.calculate_total_distances(bike_distances)
            try:
                min_bike_distance = min(bike_total_distances)
            except ValueError:
                min_bike_distance = -1
                N.vehicles.count = N.vehicles.count + 1
                print(f"T{thread}: adding bike {N.vehicles.count}")

        index = bike_total_distances.index(min_bike_distance)

        bike_count = len(bike_routes[index])
        print(f"T{thread}: best total bike distance: {min_bike_distance}\n")

        print(f"T{thread}: van:")
        min_van_distance = -1
        N.vehicles = N.vans
        while min_van_distance == -1:
            van_routes, van_distances, N = CVRP.solve(N, timeout=timeout)
            van_total_distances = CVRP.calculate_total_distances(van_distances)

            try:
                min_van_distance = min(van_total_distances)
            except ValueError:
                min_van_distance = -1
                N.vehicles.count = N.vehicles.count + 1
                print(f"T{thread}: adding van {N.vehicles.count}")

        index = van_total_distances.index(min_van_distance)

        van_count = len(van_routes[index])

        print(f"T{thread}: best total van distance: {min_van_distance}\n")

        van_emissions = co2.calc_co2(van_count, min_van_distance / 1000, co2.cons, co2.em_fs, params=[0, 100])

        result = N, bike_routes, bike_distances, min_bike_distance, bike_count, van_routes, van_distances, min_van_distance, van_count, van_emissions
        q.put(result)


if __name__ == "__main__":

    # just for experiments, will be deleted later
    boundaries_krakow = (
        (19.9361, 50.0661), (19.9419, 50.0655), (19.9447, 50.0644), (19.9436, 50.0609), (19.9406, 50.0587),
        (19.9389, 50.0546), (19.9375, 50.0555), (19.9352, 50.0557), (19.9334, 50.0589), (19.9319, 50.0619))
    krakow_loadpoint = [19.9391056, 50.06626309999999]

    boundaries_mechelen = (
        (4.4822036, 51.0213959), (4.4866775, 51.026221), (4.4851111, 51.0289134), (4.4824289, 51.0306475),
        (4.4799184, 51.0308567), (4.4756054, 51.0292305), (4.474554, 51.0259916), (4.4741677, 51.0238726),
        (4.4822036, 51.0213959))
    mecheln_loadpoint = [4.482073, 51.022549]

    boundaries_vitoria = (

        (-2.6766654, 42.8458424), (-2.6752331, 42.8451029), (-2.6757642, 42.8431953), (-2.6711347, 42.8425935),
        (-2.6691767, 42.843333), (-2.6689407, 42.8449535), (-2.6700833, 42.8460823), (-2.6738652, 42.8464323),
        (-2.6766654, 42.8458424))
    vitoria_loadpoint = [2.6725242000000002, 42.843152599999996]

    boundaries_san_sebastian = (
        (-1.9807414, 43.323346), (-1.9820718, 43.3251411), (-1.9842283, 43.3259841), (-1.9882409, 43.3240094),
        (-1.9867281, 43.321582), (-1.9807414, 43.323346))
    ss_loadpoint = [-1.98356005903998, 43.3241469483965]

    boundaries_rimini = (
        (12.5615, 44.0654), (12.5641, 44.0634), (12.5638, 44.0617), (12.5628, 44.0605), (12.5633, 44.059),
        (12.566, 44.0565), (12.5697, 44.056), (12.5736, 44.0582), (12.5739, 44.0595), (12.5721, 44.0616),
        (12.567, 44.0655), (12.5651, 44.0662), (12.5629, 44.0666), (12.5615, 44.0654))
    rimini_loadpoint = [12.570303976535799, 44.056744178234275]

    experiment_list = []
    experiment_list.append({
        'city': 'krakow',
        'boundaries': boundaries_krakow,
        'loadpoint': krakow_loadpoint})

    experiment_list.append({
        'city': 'mechelen',
        'boundaries': boundaries_mechelen,
        'loadpoint': mecheln_loadpoint})

    experiment_list.append({
        'city': 'vitoria',
        'boundaries': boundaries_vitoria,
        'loadpoint': vitoria_loadpoint})

    experiment_list.append({
        'city': 'san_sebastian',
        'boundaries': boundaries_san_sebastian,
        'loadpoint': ss_loadpoint})

    experiment_list.append({
        'city': 'rimini',
        'boundaries': boundaries_rimini,
        'loadpoint': rimini_loadpoint})

    for single_experiment in experiment_list:

        n = net.Net()
        #
        # n.bbox = net.AreaBoundingBox(longitude_west=19.93000, longitude_east=19.94537, latitude_south=50.05395,
        #                              latitude_north=50.06631)

        city_name = single_experiment['city']

        n.polygon = net.AreaBoundingPolygon(single_experiment['boundaries'])

        if n.bbox is None and n.polygon is None:
            n = net_draw.create_bounding_polygon(n)

        n = OSM_download.generate_network_and_businesses(n)

        # just for experiments, will be deleted later
        load_point = node.Node(nid=n.nodes[-1].nid + 1, name="Load Point")
        load_point.x = single_experiment['loadpoint'][0]
        load_point.y = single_experiment['loadpoint'][1]
        load_point.type = 'L'
        n.nodes.append(load_point)
        n.set_closest_itsc()

        if len([node for node in n.nodes if node.type == 'L']) == 0:
            n = net_draw.select_loading_point(n)

        net_draw.draw_results(n)

        # TODO add better probs weights and dimensions, pack this into another file
        probs = {'F_D': 0.3, 'L_B': 0.1, 'C_S': 0.4, 'V_S': 0.15, 'O_S': 0.05, 'O': 0.05, 'N': 0, 'L': 0}

        weightLaw = 0  # 0 - rectangular, 1 - normal, 2 - exponential
        weightLocation = 0  # grams
        weightScale = 25000  # 25kg for UPS, InPost, 31,5 kg for for DPD, DHL

        dimensionsLaw = 0
        dimensionsLocation = 0  # mm
        dimensionsScale = 400

        experiment_per_thread = 15
        timeout = 100

        s_weight = stochastic.Stochastic(law=weightLaw, location=weightLocation, scale=weightScale)
        s_dimensions = stochastic.Stochastic(law=dimensionsLaw, location=dimensionsLocation, scale=dimensionsScale)

        lpoints = [node for node in n.nodes if node.type == 'L']
        sender = lpoints[0]

        n.vans = vehicles.Vehicles(common.load_dict_from_json("data/data_model_van.json"))
        n.bikes = vehicles.Vehicles(common.load_dict_from_json("data/data_model_bike.json"))

        if city_name == "":
            folder_name = f"{n.bbox.__str__().replace(',', '_').strip('()')}"
        else:
            folder_name = city_name

        folder_name = folder_name + f"_{weightLaw}_law_{weightLocation}_location_{weightScale}_scale_{dimensionsLaw}_dimLaw_{dimensionsLocation}_dimLoc{dimensionsScale}_dimScale"
        folder_path = 'results/CVRP/' + folder_name
        absolute_folder_path = os.getcwd() + '/' + folder_path
        Path(absolute_folder_path).mkdir(parents=True, exist_ok=True)

        manager = mp.Manager()
        q = manager.Queue()

        pool = mp.Pool(mp.cpu_count() + 2)

        watcher = pool.apply_async(listener, (q,))

        jobs = []
        for i in range(mp.cpu_count()):
            job = pool.apply_async(experiment, args=(n, i, q, experiment_per_thread, timeout))
            jobs.append(job)

        for job in jobs:
            job.get()

        q.put("kill")
        pool.close()
        pool.join()
