from scripts.cbsim.net import Net
from scripts.cbsim import stochastic
import scripts.cbsim.cvrp_multi_route as cvrp
import scripts.cbsim.common as common


def results_handler(info, n):
    if info['solver_status'] != 1:
        print(f"solver status: {info['solver_status']}")
    else:
        if len(info['dropped_orders']) != 0:
            time_usage = n.vehicles.time / info['time']
            distance_usage = info['distance'] / n.vehicles.distance

            print(f"time%: {time_usage}; distance%: {distance_usage}")
            dropped_orders = sorted(info['dropped_orders'], reverse=True)
            print(f"dropped orders: {len(dropped_orders)}")
            for order in dropped_orders:
                n.demand.pop(order)


# get net with no orders, intersection sdm and vehicles

def main(n: Net):
    # run at first with 0 bicycles, then add one
    max_bikes = 5
    # limits obtained experimentally basing on the Kraków city center
    timeout = 600
    solution_limit = 2000

    results = []
    probs = {'F_D': 0.3, 'L_B': 0.1, 'C_S': 0.4, 'V_S': 0.15, 'O_S': 0.05, 'O': 0.05, 'N': 0, 'L': 0}

    weightLaw = 0  # 0 - rectangular, 1 - normal, 2 - exponential
    weightLocation = 50  # grams
    weightScale = 150000  # 25kg for UPS, InPost, 31,5 kg for for DPD, DHL

    dimensionsLaw = 0
    dimensionsLocation = 10  # mm
    dimensionsScale = 1000

    s_weight = stochastic.Stochastic(law=weightLaw, location=weightLocation, scale=weightScale)
    s_dimensions = stochastic.Stochastic(law=dimensionsLaw, location=dimensionsLocation, scale=dimensionsScale)

    multithreading = False


    lpoints = [node for node in n.nodes if node.type == 'L']

    for bike_count in range(max_bikes):
        n.demand = []
        print(f'bike count: {bike_count}')
        n.gen_requests(sender=lpoints[0], nodes=n.nodes, probs=probs, s_weight=s_weight, s_dimensions=s_dimensions)
        # iterate over bicycles, if none dont't
        if bike_count != 0:
            for bike in range(bike_count):
                n.vehicles = n.bikes
                info = cvrp.solve(n, timeout, solution_limit)
                print(f"bike: {bike}")
                results_handler(info, bike)
                info['type'] = "bike"
                results.append(info)
                if not n.demand:
                    continue
        print('van')
        for i in range(5):
            if n.demand is not []:
                n.vehicles = n.vans
                info = cvrp.solve(n, timeout, solution_limit)
                results_handler(info, n)
                print(f'van: {i}')
                info['type'] = "van"
                results.append(info)
                if not n.demand:
                    continue
    common.save_results("/results/test.txt")
    return results



    # expected output:
    # routes for all vehicles
    # time, distance, for each vehicle
    # if there are undelivered orders(shouldn't be)
