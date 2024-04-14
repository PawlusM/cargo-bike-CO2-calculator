import time

from scripts.cbsim import OSM_download, net, net_draw, node, stochastic, common, vehicles, CVRP, co2, experiment_runner
from datetime import datetime
from pathlib import Path
import multiprocessing as mp
import os

kill = False


def listener(q):

    counter = 0
    while True:
        message = q.get()

        # print(f"got: {message}")
        if message == "kill" or kill == True:

            kill = True
            print("kill")
            break
        else:
            counter += 1
            (results, demands, total_info) = message
        results_saver(results, demands, total_info)



def results_saver(results, demands, total_info):
    now = datetime.now()
    dtString = now.strftime("%Y_%m_%d_%H_%M_%S_%s")

    Path(absolute_folder_path + '/demands').mkdir(parents=True, exist_ok=True)
    Path(absolute_folder_path + '/results').mkdir(parents=True, exist_ok=True)

    common.save_dict_to_json(demands, absolute_folder_path + f'/demands/{dtString}.json')
    common.save_dict_to_json(results, absolute_folder_path + f'/results/{dtString}.json')

    results_path = absolute_folder_path + '/' + "results.csv"
    if not (os.path.isfile(results_path)):
        with open(results_path, 'w') as f:
            f.write(
                "datetime;bike_count;bike_total_distance;bike_total_time;van_count;van_total_distance;van_total_time;van_emissions\n")

    for i in range(len(total_info['bike_distances'])):
        bike_count = i
        bike_total_distance = total_info['bike_distances'][i]
        bike_total_time = total_info['bike_times'][i]
        van_count = total_info['van_count'][i]
        van_total_distance = total_info['van_distances'][i]
        van_total_time = total_info['van_times'][i]
        van_emissions = total_info['van_emissions'][i]

        with open(results_path, 'a') as f:
            f.write(
                f"{dtString};{bike_count};{bike_total_distance};{bike_total_time};{van_count};{van_total_distance};{van_total_time};{van_emissions}\n")

def experiment(N, q, thread):
    experiment_per_thread = 15

    for i in range(experiment_per_thread):
        results, demands, total_data = experiment_runner.main(N, thread)
        # results = [1]
        # demands = [2]
        # total_data = [3]
        q.put((results, demands, total_data))
        return results, demands, total_data
        # print(f"T{thread}: bike:")
        # min_bike_distance = -1
        #
        # N.vehicles = N.bikes
        # while min_bike_distance == -1:
        #     bike_routes, bike_distances, N = cvrp_multi_route.solve(N, timeout=timeout, solution_limit = 100)
        #     bike_total_distances = CVRP.calculate_total_distances(bike_distances)
        #     try:
        #         min_bike_distance = min(bike_total_distances)
        #     except ValueError:
        #         min_bike_distance = -1
        #         N.vehicles.count = N.vehicles.count + 1
        #         print(f"T{thread}: adding bike {N.vehicles.count}")
        #
        # index = bike_total_distances.index(min_bike_distance)
        #
        # bike_count = len(bike_routes[index])
        # print(f"T{thread}: best total bike distance: {min_bike_distance}\n")
        #
        # print(f"T{thread}: van:")
        # min_van_distance = -1
        # N.vehicles = N.vans
        # while min_van_distance == -1:
        #     van_routes, van_distances, N = CVRP.solve(N, timeout=timeout)
        #     van_total_distances = CVRP.calculate_total_distances(van_distances)
        #
        #     try:
        #         min_van_distance = min(van_total_distances)
        #     except ValueError:
        #         min_van_distance = -1
        #         N.vehicles.count = N.vehicles.count + 1
        #         print(f"T{thread}: adding van {N.vehicles.count}")
        #
        # index = van_total_distances.index(min_van_distance)
        #
        # van_count = len(van_routes[index])
        #
        # print(f"T{thread}: best total van distance: {min_van_distance}\n")
        #
        # van_emissions = co2.calc_co2(van_count, min_van_distance / 1000, co2.cons, co2.em_fs, params=[0, 100])
        #
        # result = N, bike_routes, bike_distances, min_bike_distance, bike_count, van_routes, van_distances, min_van_distance, van_count, van_emissions
        # q.put(result)


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

# experiment_list.append({
#     'city': 'mechelen',
#     'boundaries': boundaries_mechelen,
#     'loadpoint': mecheln_loadpoint})
#
# experiment_list.append({
#     'city': 'vitoria',
#     'boundaries': boundaries_vitoria,
#     'loadpoint': vitoria_loadpoint})

# experiment_list.append({
#     'city': 'san_sebastian',
#     'boundaries': boundaries_san_sebastian,
#     'loadpoint': ss_loadpoint})

# experiment_list.append({
#     'city': 'rimini',
#     'boundaries': boundaries_rimini,
#     'loadpoint': rimini_loadpoint})

for single_experiment in experiment_list:

    n = net.Net()

    n.city_name = single_experiment['city']

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

    # net_draw.draw_results(n)


    multithreading = False


    lpoints = [node for node in n.nodes if node.type == 'L']
    sender = lpoints[0]

    n.vans = vehicles.Vehicles(common.load_dict_from_json("data/data_model_van.json"))
    n.bikes = vehicles.Vehicles(common.load_dict_from_json("data/data_model_bike.json"))

    city_name = n.city_name

    if city_name == "":
        folder_name = f"{n.bbox.__str__().replace(',', '_').strip('()')}"
    else:
        folder_name = city_name

    # folder_name = folder_name + f"_{weightLaw}_law_{weightLocation}_location_{weightScale}_scale_{dimensionsLaw}_dimLaw_{dimensionsLocation}_dimLoc{dimensionsScale}_dimScale"
    folder_name = folder_name + "_multiroute"
    folder_path = 'results/CVRP/' + folder_name
    absolute_folder_path = os.getcwd() + '/' + folder_path
    Path(absolute_folder_path).mkdir(parents=True, exist_ok=True)

    manager = mp.Manager()
    q = manager.Queue()


    if multithreading:
        pool = mp.Pool(mp.cpu_count() + 2)

        watcher = pool.apply_async(listener, (q,))

        jobs = []
        for i in range(mp.cpu_count()):
            job = pool.apply_async(experiment, args=(n, q, i))
            jobs.append(job)

        for job in jobs:
            job.get()

        q.put("kill")
        print("Experiment finished")
        pool.close()
        pool.join()
    else:

        results, demands, total_data = experiment(n, q, 0)
        results_saver(results, demands, total_data)
