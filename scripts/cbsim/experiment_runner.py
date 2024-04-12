from scripts.cbsim.net import Net
from scripts.cbsim import stochastic, common, co2
import scripts.cbsim.cvrp_multi_route as cvrp
import os


def results_handler(info, n):
    # print(f"solver status: {info['solver_status']}")

    time_usage = info['time'] / n.vehicles.time
    distance_usage = info['distance'] / n.vehicles.distance

    # print(f"time%: {time_usage}; distance%: {distance_usage}")
    completed_orders = list(filter(lambda x: x >= 0, sorted(info['route'], reverse=True)))

    # print(f"completed orders: {len(completed_orders)}")
    for order in completed_orders:
        if order < 0:
            #     depot or reloading point(same location, multiplied for solver), do nothing
            pass
        else:
            n.demand.pop(order)


# get net with no orders, intersection sdm and vehicles

def main(n: Net, thread: int):
    # run at first with 0 bicycles, then add one
    max_bikes = 5
    # limits obtained experimentally basing on the Kraków city center
    timeout = 1200
    solution_limit = 2000

    results = {}
    probs = {'F_D': 0.3, 'L_B': 0.1, 'C_S': 0.4, 'V_S': 0.15, 'O_S': 0.05, 'O': 0.05, 'N': 0, 'L': 0}

    weightLaw = 1  # 0 - rectangular, 1 - normal, 2 - exponential
    weightLocation = 75000  # grams
    # weightScale = 150000  # 25kg for UPS, InPost, 31,5 kg for for DPD, DHL

    dimensionsLaw = 1
    dimensionsLocation = 500  # mm
    # dimensionsScale = 1000

    s_weight = stochastic.Stochastic(law=weightLaw, location=weightLocation, scale=0.3 * weightLocation)
    s_dimensions = stochastic.Stochastic(law=dimensionsLaw, location=dimensionsLocation, scale=0.3 * dimensionsLocation)

    lpoints = [node for node in n.nodes if node.type == 'L']

    n.gen_requests(sender=lpoints[0], nodes=n.nodes, probs=probs, s_weight=s_weight, s_dimensions=s_dimensions)

    filename = f'data/net_copy_{thread}.pkl'

    common.save_results(filename, n)

    demands = []

    for single_demand in n.demand:
        demand = {}
        demand['destination'] = single_demand.destination.name
        demand['weight'] = single_demand.weight
        demand['volume'] = single_demand.volume
        demands.append(demand)

    for bike_count in range(max_bikes):
        results[bike_count] = []
        # print(f'bike count: {bike_count}')
        n = common.load_results(filename)
        # common.save_results()
        # iterate over bicycles, if none dont't
        if bike_count != 0:
            for bike in range(bike_count):
                n.vehicles = n.bikes
                # print(f"bike: {bike}, total orders = {len(n.demand)}")
                info = cvrp.solve(n, timeout, solution_limit)

                results_handler(info, n)
                info['type'] = "bike"

                results[bike_count].append(info)
                if not n.demand:
                    break
        # print('van')
        for i in range(5):
            if n.demand is not []:
                n.vehicles = n.vans
                # print(f"van: {i}, total orders = {len(n.demand)}")
                info = cvrp.solve(n, timeout, solution_limit)
                results_handler(info, n)

                info['type'] = "van"
                results[bike_count].append(info)
                if not n.demand:
                    break
    os.remove(filename)

    bike_distances = []
    bike_times = []
    van_distances = []
    van_times = []
    van_emissions = []
    van_counts = []

    for single_result in results:
        bike_total_distance = 0
        bike_total_time = 0
        van_total_distance = 0
        van_total_time = 0
        van_count = 0
        for single_vehicle in results[single_result]:
            if single_vehicle['type'] == "van":
                van_total_distance += single_vehicle['distance']
                van_total_time += single_vehicle['time']
                van_count += 1
            elif single_vehicle['type'] == "bike":
                bike_total_distance += single_vehicle['distance']
                bike_total_time += single_vehicle['time']
        bike_distances.append(bike_total_distance)
        bike_times.append(bike_total_time)
        van_distances.append(van_total_distance)
        van_times.append(van_total_time)
        van_counts.append(van_count)
        van_emissions.append(co2.calc_co2(van_count, van_total_distance / 1000, co2.cons, co2.em_fs, params=[0, 100]))
    total_data = {'bike_distances': bike_distances,
                  'bike_times': bike_times,
                  'van_count' : van_counts,
                  'van_distances': van_distances,
                  'van_times': van_times,
                  'van_emissions': van_emissions}
    print(f'thread: {thread} done')
    return results, demands, total_data

    # expected output:
    # routes for all vehicles
    # time, distance, for each vehicle
    # if there are undelivered orders(shouldn't be)
