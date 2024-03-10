from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from ortools.constraint_solver.pywrapcp import SolutionCollector

from scripts.cbsim import net
from math import ceil
import numpy as np


# TODO consider moving vehicle count calculation to net.py
def prepare_data(n: net.Net):
    #   Calculate how many vehicles are needed to fulfill the demands
    sum_weights = 0
    sum_volumes = 0

    for single_demand in n.demand:
        sum_weights += single_demand.weight
        sum_volumes += single_demand.volume

    vehicle_count_weight = sum_weights / n.vehicles.capacity
    vehicle_count_volume = sum_volumes / n.vehicles.cargo_volume

    # TODO change to max()
    if vehicle_count_weight >= vehicle_count_volume:
        n.vehicles.count = ceil(vehicle_count_weight)
    else:
        n.vehicles.count = ceil(vehicle_count_volume)

    n.vehicles.capacities = []
    n.vehicles.volumes = []
    for i in range(n.vehicles.count):
        n.vehicles.capacities.append(n.vehicles.capacity)
        n.vehicles.volumes.append(n.vehicles.cargo_volume)

    #   generate SDM for routing problem
    lpoints = [node for node in n.nodes if node.type == 'L']
    sender = lpoints[0]
    destinations_nid = []
    destinations_nid.append(sender.closest_itsc.nid)
    for i in range(len(n.demand)):
        destinations_nid.append(n.demand[i].destination.closest_itsc.nid)

    requests_sdm = np.zeros((len(destinations_nid), len(destinations_nid)), dtype=int)

    for sdm_i, from_node_id in enumerate(destinations_nid):
        for sdm_j, to_node_id in enumerate(destinations_nid):
            requests_sdm[sdm_i, sdm_j] = round(n.sdm[from_node_id][to_node_id] * 1000)

    # for i in range(len(requests_sdm)):
    #     for j in range(len(requests_sdm)):
    #         if i == j:
    #             requests_sdm[i][j] = 0
    #         else:
    #             from_node_id = n.demand[i - 1].destination.closest_itsc.nid
    #             to_node_id = n.demand[j - 1].destination.closest_itsc.nid
    #             value = n.sdm[from_node_id][to_node_id]*1000
    #             requests_sdm[i][j] = round(n.sdm[from_node_id][to_node_id]*1000)

    data = {}
    data['num_vehicles'] = n.vehicles.count
    data['vehicle_capacities'] = n.vehicles.capacities
    data['cargo_volume'] = n.vehicles.cargo_volume
    data['vehicle_load'] = []
    data['depotID'] = 0
    for i in range(0, data['num_vehicles']):
        data['vehicle_load'].append(0)

    print(f"Number of vehicles: {data['num_vehicles']}")

    orders = {
        "ID": [0],  # 0 is the depot
        "weight": [0],  # g
        "width": [0],
        "length": [0],  # mm
        "height": [0],
        "volume": [0]
    }

    for ID, singleOrder in enumerate(n.demand):
        orders['ID'].append(singleOrder.destination.closest_itsc.nid)
        orders['weight'].append(singleOrder.weight)
        orders['width'].append(singleOrder.width)
        orders['length'].append(singleOrder.length)
        orders['height'].append(singleOrder.height)
        orders['volume'].append(singleOrder.volume)

    return data, orders, requests_sdm


def solve(n: net.Net, timeout):
    data, orders, distance_matrix = prepare_data(n)
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), data['num_vehicles'], data['depotID'])

    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define distance of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # volume constraints
    def volume_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return orders['volume'][from_node]

    # volume constraint
    volume_callback_index = routing.RegisterUnaryTransitCallback(volume_callback)

    routing.AddDimension(
        volume_callback_index,
        0,  # null capacity slack
        data['cargo_volume'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Volume')

    # weight constraints
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return orders['weight'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        999999,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.solution_limit = 1
    search_parameters.time_limit.FromSeconds(timeout)
    search_parameters.use_full_propagation = 1

    # Solve the problem.

    assignment = routing.SolveWithParameters(search_parameters)
    collector = initialize_collector(data, manager, routing, distance_matrix)

    search_parameters.solution_limit = 2 ** 24
    search_parameters.time_limit.FromSeconds(timeout)

    routing.SolveFromAssignmentWithParameters(assignment, search_parameters)

    routes = []
    distances = []

    # Print solution on console.
    if assignment:

        print('CVRP feasible solutions: {}'.format(collector.SolutionCount()))
        for i in range(collector.SolutionCount()):
            temp_route, temp_distance = list_solution(data,
                                                      manager,
                                                      routing,
                                                      collector.Solution(i),
                                                      i,
                                                      distance_matrix)

            routes.append(temp_route)
            distances.append(temp_distance)
    else:
        print("No solutions")

    return routes, distances


def initialize_collector(data, manager, routing, distance_matrix):
    collector: SolutionCollector = routing.solver().AllSolutionCollector()
    collector.AddObjective(routing.CostVar())

    routing.AddSearchMonitor(collector)

    for node in range(len(distance_matrix)):
        collector.Add(routing.NextVar(manager.NodeToIndex(node)))

    for v in range(data['num_vehicles']):
        collector.Add(routing.NextVar(routing.Start(v)))

    return collector


def list_solution(data, manager, routing, solution, i, distance_matrix):
    routes = []
    distances = []

    total_distance = 0
    max_route_distance = 0

    for vehicle_id in range(data['num_vehicles']):
        tempsolution = []
        index = routing.Start(vehicle_id)

        route_distance = 0
        route = []
        distance = []
        previous_index = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            # print('INDEX {}'.format(node_index))
            # print('PREV_INDEX {}'.format(previous_index))
            route.append(node_index)
            # print(distance_matrix[previous_index][node_index])
            distance.append(distance_matrix[previous_index][node_index])
            previous_index = node_index
            index = solution.Value(routing.NextVar(index))

        route.append(data['depotID'])
        distance.append(distance_matrix[previous_index][data['depotID']])
        routes.append(route)
        distances.append(distance)

    return routes, distances

def calculate_total_distances(routes):
    total_distances = []
    for route in routes:
        single_total_distance = 0
        for vehicle in route:
            single_total_distance += sum(vehicle)
        total_distances.append(single_total_distance)
    return total_distances