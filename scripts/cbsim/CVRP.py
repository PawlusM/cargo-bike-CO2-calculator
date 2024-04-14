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
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH)
    search_parameters.solution_limit = solution_limit
    search_parameters.time_limit.FromSeconds(
        timeout)  # high time limit in order to accommodate for slow cpus or not having
    # enough solution to trigger solution_limit

    search_parameters.use_full_propagation = 1

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

# def solve(n: net.Net, timeout):
#     data, orders, distance_matrix, n = prepare_data(n)
#     manager = pywrapcp.RoutingIndexManager(len(distance_matrix), data['num_vehicles'], data['depotID'])
#
#     routing = pywrapcp.RoutingModel(manager)
#
#     # Create and register a transit callback.
#     def distance_callback(from_index, to_index):
#         """Returns the distance between the two nodes."""
#         # Convert from routing variable Index to distance matrix NodeIndex.
#         from_node = manager.IndexToNode(from_index)
#         to_node = manager.IndexToNode(to_index)
#         # distance = distance_matrix[from_node][to_node] + orders['itsc_distance'][to_node]
#         return distance_matrix[from_node][to_node]
#
#     transit_callback_index = routing.RegisterTransitCallback(distance_callback)
#
#     # Define distance of each arc.
#     routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
#
#     # volume constraints
#     def volume_callback(from_index):
#         from_node = manager.IndexToNode(from_index)
#         return orders['volume'][from_node]
#
#     # volume constraint
#     volume_callback_index = routing.RegisterUnaryTransitCallback(volume_callback)
#
#     routing.AddDimension(
#         volume_callback_index,
#         0,  # null capacity slack
#         data['cargo_volume'],  # vehicle maximum capacities
#         True,  # start cumul to zero
#         'Volume')
#
#     # weight constraints
#     def demand_callback(from_index):
#         from_node = manager.IndexToNode(from_index)
#         return orders['weight'][from_node]
#
#     demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
#
#     routing.AddDimensionWithVehicleCapacity(
#         demand_callback_index,
#         0,  # null capacity slack
#         data['vehicle_capacities'],  # vehicle maximum capacities
#         True,  # start cumul to zero
#         'Capacity')
#
#     dimension_name = 'Distance'
#     routing.AddDimension(
#         transit_callback_index,
#         0,  # no slack
#         999999,  # vehicle maximum travel distance
#         True,  # start cumul to zero
#         dimension_name)
#     distance_dimension = routing.GetDimensionOrDie(dimension_name)
#     distance_dimension.SetGlobalSpanCostCoefficient(100)
#
#     # Setting first solution heuristic.
#     search_parameters = pywrapcp.DefaultRoutingSearchParameters()
#     search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
#     search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
#     search_parameters.solution_limit = 100
#     search_parameters.time_limit.FromSeconds(timeout)
#     search_parameters.use_full_propagation = 1
#
#     # Solve the problem.
#
#     assignment = routing.SolveWithParameters(search_parameters)
#     collector = initialize_collector(data, manager, routing, distance_matrix)
#
#     search_parameters.solution_limit = 2 ** 24
#     search_parameters.time_limit.FromSeconds(timeout)
#
#     routing.SolveFromAssignmentWithParameters(assignment, search_parameters)
#
#     routes = []
#     distances = []
#
#     # Print solution on console.
#     if assignment:
#
#         print('CVRP feasible solutions: {}'.format(collector.SolutionCount()))
#         for i in range(collector.SolutionCount()):
#             temp_route, temp_distance = list_solution(data,
#                                                       manager,
#                                                       routing,
#                                                       collector.Solution(i),
#                                                       i,
#                                                       distance_matrix)
#
#             routes.append(temp_route)
#             distances.append(temp_distance)
#     else:
#         print("No solutions")
#
#     return routes, distances, n
#
#
# def initialize_collector(data, manager, routing, distance_matrix):
#     collector: SolutionCollector = routing.solver().AllSolutionCollector()
#     collector.AddObjective(routing.CostVar())
#
#     routing.AddSearchMonitor(collector)
#
#     for node in range(len(distance_matrix)):
#         collector.Add(routing.NextVar(manager.NodeToIndex(node)))
#
#     for v in range(data['num_vehicles']):
#         collector.Add(routing.NextVar(routing.Start(v)))
#
#     return collector
#
#
# def list_solution(data, manager, routing, solution, i, distance_matrix):
#     routes = []
#     distances = []
#
#     total_distance = 0
#     max_route_distance = 0
#
#     for vehicle_id in range(data['num_vehicles']):
#         tempsolution = []
#         index = routing.Start(vehicle_id)
#
#         route_distance = 0
#         route = []
#         distance = []
#         previous_index = 0
#         while not routing.IsEnd(index):
#             node_index = manager.IndexToNode(index)
#             # print('INDEX {}'.format(node_index))
#             # print('PREV_INDEX {}'.format(previous_index))
#             route.append(node_index)
#             # print(distance_matrix[previous_index][node_index])
#             distance.append(distance_matrix[previous_index][node_index])
#             previous_index = node_index
#             index = solution.Value(routing.NextVar(index))
#
#         route.append(data['depotID'])
#         distance.append(distance_matrix[previous_index][data['depotID']])
#         routes.append(route)
#         distances.append(distance)
#
#     return routes, distances
#
#
# def calculate_total_distances(routes):
#     total_distances = []
#     for route in routes:
#         single_total_distance = 0
#         for vehicle in route:
#             single_total_distance += sum(vehicle)
#         total_distances.append(single_total_distance)
#     return total_distances
