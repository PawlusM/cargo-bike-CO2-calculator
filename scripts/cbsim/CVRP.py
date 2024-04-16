import random
import time

from ortools.constraint_solver import routing_enums_pb2, pywrapcp

import numpy as np
from functools import partial


# CVRP with mass, volume, max time and max distance limit


def prepare_data(demands, load_point, sdm, vehicle):
    # lpoints = [node for node in n.nodes if node.type == 'L']
    # sender = lpoints[0]

    #   generate SDM for routing problem

    destinations_nid = []
    destinations_nid.append(load_point.closest_itsc.nid)
    for i in range(len(demands)):
        destinations_nid.append(demands[i].destination.closest_itsc.nid)

    requests_sdm = np.zeros((len(destinations_nid), len(destinations_nid)), dtype=int)

    for sdm_i, from_node_id in enumerate(destinations_nid):
        for sdm_j, to_node_id in enumerate(destinations_nid):
            requests_sdm[sdm_i, sdm_j] = round(sdm[from_node_id][to_node_id] * 1000)

    requests_sdm = requests_sdm.tolist()

    orders = dict(weight=[0], volume=[0])

    for ID, singleOrder in enumerate(demands):
        # orders['ID'].append(singleOrder.destination.closest_itsc.nid)
        orders['weight'].append(singleOrder.weight)
        orders['volume'].append(singleOrder.volume)
        # orders['itsc_distance'].append(
        #     int(gps_distance(singleOrder.destination, singleOrder.destination.closest_itsc) * 1000))

    data = {}
    data['distance_matrix'] = requests_sdm
    data['depot'] = 0
    data['num_locations'] = len(orders['weight'])
    data['num_vehicles'] = 1
    data['vehicle_capacity'] = vehicle.capacity
    data['cargo_volume'] = vehicle.cargo_volume
    data['vehicle_max_distance'] = vehicle.distance_left
    data['vehicle_max_time'] = vehicle.time_left
    data['vehicle_load'] = []
    data['vehicle_speed'] = vehicle.average_speed * 60 / 3.6  # Travel speed: km/h converted  in m/min
    data['service_time'] = vehicle.service_time

    # data = {'depot': 0, 'num_locations': 6, 'num_vehicles': 1, 'vehicle_capacity': 1415000,
    #         'cargo_volume': 14084823375,
    #         'vehicle_max_distance': 500000, 'vehicle_max_time': 480, 'vehicle_load': [],
    #         'vehicle_speed': 166.6666666666666,
    #         'service_time': 5, 'distance_matrix': [[]]}
    # orders = {'volume': [0, 1000, 2000, 3000, 4000, 5000], 'weight': [0, 1000, 2000, 3000, 4000, 5000]}
    #
    # data['distance_matrix'] = np.zeros((len(orders['volume']), len(orders['volume'])), dtype=int)
    # for i in range(len(orders['weight'])):
    #     for j in range(len(orders['weight'])):
    #         if i == j:
    #             data['distance_matrix'][i, j] = 0
    #         else:
    #             data['distance_matrix'][i, j] = 1000
    #
    # data['distance_matrix'] = data['distance_matrix'].tolist()

    assert len(data['distance_matrix']) == len(orders['weight']) == len(orders['volume'])

    return data, orders


def create_distance_evaluator(data):
    """Creates callback to return distance between points."""
    _distances = {}
    # precompute distance between location to have distance callback in O(1)
    for from_node in range(data['num_locations']):
        _distances[from_node] = {}
        for to_node in range(data['num_locations']):
            if from_node == to_node:
                _distances[from_node][to_node] = 0
            else:
                _distances[from_node][to_node] = (data['distance_matrix'][from_node][to_node])

    def distance_evaluator(manager, from_node, to_node):
        """Returns the manhattan distance between the two nodes"""
        return _distances[manager.IndexToNode(from_node)][manager.IndexToNode(
            to_node)]

    return distance_evaluator


def add_distance_dimension(routing, manager, data, distance_evaluator_index):
    """Add Global Span constraint"""
    del manager
    distance = 'Distance'
    routing.AddDimension(
        distance_evaluator_index,
        0,  # null slack
        data['vehicle_max_distance'],  # maximum distance per vehicle
        True,  # start cumul to zero
        distance)
    distance_dimension = routing.GetDimensionOrDie(distance)
    # Try to minimize the max distance among vehicles.
    # /!\ It doesn't mean the standard deviation is minimized
    distance_dimension.SetGlobalSpanCostCoefficient(100)


def create_demand_evaluator(orders):
    """Creates callback to get demands at each location."""
    _demands = orders['weight']

    def demand_evaluator(manager, from_node):
        """Returns the demand of the current node"""
        return _demands[manager.IndexToNode(from_node)]

    return demand_evaluator


def create_volume_evaluator(orders):
    """Creates callback to get demands at each location."""
    _demands = orders['volume']

    def volume_evaluator(manager, from_node):
        """Returns the demand of the current node"""
        return _demands[manager.IndexToNode(from_node)]

    return volume_evaluator


def add_capacity_constraints(routing, manager, data, demand_evaluator_index):
    """Adds capacity constraint"""
    vehicle_capacity = data['vehicle_capacity']

    capacity = 'Capacity'
    routing.AddDimension(
        demand_evaluator_index,
        0,
        vehicle_capacity,
        True,  # start cumul to zero
        capacity)

    # Add Slack for reseting to zero unload depot nodes.
    # e.g. vehicle with load 10/15 arrives at node 1 (depot unload)
    # so we have CumulVar = 10(current load) + -15(unload) + 5(slack) = 0.
    capacity_dimension = routing.GetDimensionOrDie(capacity)

    # Allow to drop regular node with a cost.
    for node in range(1, data['num_locations']):
        node_index = manager.NodeToIndex(node)
        # capacity_dimension.SlackVar(node_index).SetValue(0)
        routing.AddDisjunction([node_index], 100000)


def add_volume_constraints(routing, data, volume_evaluator_index):
    """Adds capacity constraint"""

    vehicle_volume = data['cargo_volume']
    volume = 'Volume'
    routing.AddDimension(
        volume_evaluator_index,
        0,
        vehicle_volume,
        True,  # start cumul to zero
        volume)


def create_time_evaluator(data):
    """Creates callback to get total times between locations."""

    def service_time(data):
        """Gets the service time for the specified location."""
        return data['service_time']

    def travel_time(data, from_node, to_node):
        """Gets the travel times between two locations."""
        if from_node == to_node:
            travel_time = 0
        else:
            travel_time = data['distance_matrix'][from_node][to_node] / data['vehicle_speed']
        return travel_time

    _total_time = {}
    # precompute total time to have time callback in O(1)
    for from_node in range(data['num_locations']):
        _total_time[from_node] = {}
        for to_node in range(data['num_locations']):
            if from_node == to_node:
                _total_time[from_node][to_node] = 0
            else:
                _total_time[from_node][to_node] = int(
                    service_time(data) +
                    travel_time(data, from_node, to_node))

    def time_evaluator(manager, from_node, to_node):
        """Returns the total time between the two nodes"""
        return _total_time[manager.IndexToNode(from_node)][manager.IndexToNode(
            to_node)]

    return time_evaluator


def add_time_constraints(routing, data, time_evaluator_index):
    """Adds time constraint"""

    max_time = data['vehicle_max_time']
    time = 'Time'
    routing.AddDimension(
        time_evaluator_index,
        0,
        max_time,
        True,  # start cumul to zero
        time)


# def print_solution(data, manager, routing, solution):
#     """Prints solution on console."""
#     print(f"Objective: {solution.ObjectiveValue()}")
#     total_distance = 0
#     total_load = 0
#     for vehicle_id in range(data["num_vehicles"]):
#         index = routing.Start(vehicle_id)
#         plan_output = f"Route for vehicle {vehicle_id}:\n"
#         route_distance = 0
#         route_load = 0
#         while not routing.IsEnd(index):
#             node_index = manager.IndexToNode(index)
#             route_load += data["demands"][node_index]
#             plan_output += f" {node_index} Load({route_load}) -> "
#             previous_index = index
#             index = solution.Value(routing.NextVar(index))
#             route_distance += routing.GetArcCostForVehicle(
#                 previous_index, index, vehicle_id
#             )
#         plan_output += f" {manager.IndexToNode(index)} Load({route_load})\n"
#         plan_output += f"Distance of the route: {route_distance}m\n"
#         plan_output += f"Load of the route: {route_load}\n"
#         print(plan_output)
#         total_distance += route_distance
#         total_load += route_load
#     print(f"Total distance of all routes: {total_distance}m")
#     print(f"Total load of all routes: {total_load}")

def print_solution(data, manager, routing, assignment):
    """Prints assignment on console"""

    print(f'Objective: {assignment.ObjectiveValue()}')
    total_distance = 0
    total_load = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    volume_dimension = routing.GetDimensionOrDie('Volume')
    time_dimension = routing.GetDimensionOrDie('Time')
    dropped = []
    for order in range(1, routing.nodes()):
        index = manager.NodeToIndex(order)
        if assignment.Value(routing.NextVar(index)) == index:
            dropped.append(order)
    print(f'dropped orders: {dropped}')

    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = f'Route for vehicle {vehicle_id}:\n'
        distance = 0
        while not routing.IsEnd(index):
            load_var = capacity_dimension.CumulVar(index)
            volume_var = volume_dimension.CumulVar(index)
            time_var = time_dimension.CumulVar(index)
            plan_output += (
                f' {manager.IndexToNode(index)} '
                f'Load({assignment.Min(load_var)}) '
                f'Volume({assignment.Min(volume_var)}) '
                f'Time({assignment.Min(time_var)},{assignment.Max(time_var)}) ->'
            )
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            distance += routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
        load_var = capacity_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        plan_output += (
            f' {manager.IndexToNode(index)} '
            f'Load({assignment.Min(load_var)}) '
            f'Time({assignment.Min(time_var)},{assignment.Max(time_var)})\n')
        plan_output += f'Distance of the route: {distance}m\n'
        plan_output += f'Load of the route: {assignment.Min(load_var)}\n'
        plan_output += f'Time of the route: {assignment.Min(time_var)}min\n'
        print(plan_output)
        total_distance += distance
        total_load += assignment.Min(load_var)
        total_time += assignment.Min(time_var)
    print(f'Total Distance of all routes: {total_distance}m')
    print(f'Total Load of all routes: {total_load}')
    print(f'Total Time of all routes: {total_time}min')


def solution_info(data, manager, routing, assignment, info):
    total_distance = 0
    total_load = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    volume_dimension = routing.GetDimensionOrDie('Volume')
    time_dimension = routing.GetDimensionOrDie('Time')
    info['route'] = []
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        distance = 0
        while not routing.IsEnd(index):
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            distance += routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            # depot has negative number so the route nodes correspond to the demand number
            info['route'].append(manager.IndexToNode(index) - 1)
        load_var = capacity_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        total_distance += distance
        total_load += assignment.Min(load_var)
        total_time += assignment.Min(time_var)
    info['time'] = total_time
    info['distance'] = total_distance
    info['load'] = total_load
    return info


def solve(demands, load_point, sdm, vehicle, solution_limit, timeout):
    data, orders = prepare_data(demands, load_point, sdm, vehicle)

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(data['num_locations'],
                                           data['num_vehicles'], data['depot'])

    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Define weight of each edge
    distance_evaluator_index = routing.RegisterTransitCallback(
        partial(create_distance_evaluator(data), manager))
    routing.SetArcCostEvaluatorOfAllVehicles(distance_evaluator_index)

    # Add Distance constraint to minimize the longest route
    add_distance_dimension(routing, manager, data, distance_evaluator_index)

    # Add Capacity constraint
    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(create_demand_evaluator(orders), manager))
    add_capacity_constraints(routing, manager, data, demand_evaluator_index)

    # Add Volume constraint
    volume_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(create_volume_evaluator(orders), manager))

    add_volume_constraints(routing, data, volume_evaluator_index)

    # Add Time  constraint
    time_evaluator_index = routing.RegisterTransitCallback(
        partial(create_time_evaluator(data), manager))
    add_time_constraints(routing, data, time_evaluator_index)

    # Setting first solution heuristic (cheapest addition).
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)  # pylint: disable=no-member
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    # search_parameters.solution_limit = solution_limit
    search_parameters.time_limit.FromSeconds(timeout)
    # enough solution to trigger solution_limit

    search_parameters.use_full_propagation = 0

    start_time = time.time()
    # Solve the problem.

    solution = routing.SolveWithParameters(search_parameters)
    runtime = time.time() - start_time
    print(runtime)

    info = {'solver_status': routing.status()}

    if solution:
        # print_solution(data, manager, routing, solution)
        info = solution_info(data, manager, routing, solution, info)
        # print(info)

    else:
        print("No solution found !")

    return info
