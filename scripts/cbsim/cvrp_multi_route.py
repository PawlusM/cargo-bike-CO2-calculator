#!/usr/bin/env python3
# This Python file uses the following encoding: utf-8
# Copyright 2015 Tin Arm Engineering AB
# Copyright 2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Capacitated Vehicle Routing Problem (CVRP).

   This is a sample using the routing library python wrapper to solve a CVRP
   problem while allowing multiple trips, i.e., vehicles can return to a depot
   to reset their load ("reload").

   A description of the CVRP problem can be found here:
   http://en.wikipedia.org/wiki/Vehicle_routing_problem.

   Distances are in meters.

   In order to implement multiple trips, new nodes are introduced at the same
   locations of the original depots. These additional nodes can be dropped
   from the schedule at 0 cost.

   The max_slack parameter associated to the capacity constraints of all nodes
   can be set to be the maximum of the vehicles' capacities, rather than 0 like
   in a traditional CVRP. Slack is required since before a solution is found,
   it is not known how much capacity will be transferred at the new nodes. For
   all the other (original) nodes, the slack is then re-set to 0.

   The above two considerations are implemented in `add_capacity_constraints()`.

   Last, it is useful to set a large distance between the initial depot and the
   new nodes introduced, to avoid schedules having spurious transits through
   those new nodes unless it's necessary to reload. This consideration is taken
   into account in `create_distance_evaluator()`.
"""

from functools import partial

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from scripts.cbsim import net

import numpy as np
import time


###########################
# Problem Data Definition #
###########################
def create_data_model(n: net.Net):
    """Stores the data for the problem"""
    data = {}

    sum_weights = 0
    sum_volumes = 0

    for single_demand in n.demand:
        sum_weights += single_demand.weight
        sum_volumes += single_demand.volume

    reload_count_weight = sum_weights / n.vehicles.capacity
    reload_count_volume = sum_volumes / n.vehicles.cargo_volume

    data['reloads'] = int(max(reload_count_weight, reload_count_volume) + 1)  # give one more reload just in case
    print(f'Reload count: {data["reloads"]}')

    # create data matrix

    lpoints = [node for node in n.nodes if node.type == 'L']
    sender = lpoints[0]
    destinations_nid = []
    destinations_nid.append(sender.closest_itsc.nid)
    for i in range(data['reloads'] - 1):
        destinations_nid.append(sender.closest_itsc.nid)

    for i in range(len(n.demand)):
        destinations_nid.append(n.demand[i].destination.closest_itsc.nid)

    requests_sdm = np.zeros((len(destinations_nid), len(destinations_nid)), dtype=int)

    for sdm_i, from_node_id in enumerate(destinations_nid):
        for sdm_j, to_node_id in enumerate(destinations_nid):
            requests_sdm[sdm_i, sdm_j] = round(n.sdm[from_node_id][to_node_id] * 1000)

    for i in range(data['reloads']):
        for j in range(data['reloads']):
            if i == j:
                requests_sdm[i, j] = 0
            else:
                requests_sdm[i, j] = 10000

    data['distance_matrix'] = requests_sdm

    # Prepare vehicle data

    _capacity = n.vehicles.capacity


    _cargo_volume = n.vehicles.cargo_volume

    data['demands'] = [0]
    data['volumes'] = [0]
    for i in range(data['reloads'] - 1):
        data['demands'].append(-_capacity)
        data['volumes'].append(-_cargo_volume)

    for ID, singleOrder in enumerate(n.demand):
        data['demands'].append(singleOrder.weight)
        data['volumes'].append(singleOrder.volume)

    # data['demands'] = \
    #     [0,  # depot
    #      -_capacity,  # unload depot_first
    #      -_capacity,  # unload depot_second
    #      -_capacity,  # unload depot_third
    #      -_capacity,  # unload depot_fourth
    #      -_capacity,  # unload depot_fifth
    #      3, 3,  # 1, 2
    #      3, 4,  # 3, 4
    #      3, 4,  # 5, 6
    #      3, 8,  # 7, 8
    #      3, 3,  # 9,10
    #      3, 3,  # 11,12
    #      4, 4,  # 13, 14
    #      8, 8]  # 15, 16
    data['num_locations'] = len(data['demands'])

    data['service_time'] = n.vehicles.service_time

    data['num_vehicles'] = 1
    data['vehicle_capacity'] = _capacity
    data["vehicle_cargo_volume"] = _cargo_volume
    data['vehicle_max_distance'] = n.vehicles.distance
    data['vehicle_max_time'] = n.vehicles.time  # 8h

    # Omitting time windows
    data['time_windows'] = [(0, 0)]  # depot
    for index in range(len(data['demands']) - 1):
        data['time_windows'].append((0, data['vehicle_max_time']))

    data[
        'vehicle_speed'] = n.vehicles.average_speed * 60 / 3.6  # Travel speed: km/h converted  in m/min
    data['depot'] = 0
    return data


#######################
# Problem Constraints #
#######################

def create_distance_evaluator(data):
    """Creates callback to return distance between points."""
    _distances = {}
    # precompute distance between location to have distance callback in O(1)
    for from_node in range(data['num_locations']):
        _distances[from_node] = {}
        for to_node in range(data['num_locations']):
            if from_node == to_node:
                _distances[from_node][to_node] = 0
            # Forbid start/end/reload node to be consecutive.
            elif from_node in range(data['reloads']) and to_node in range(data['reloads']):
                _distances[from_node][to_node] = data['vehicle_max_distance']
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


def create_demand_evaluator(data):
    """Creates callback to get demands at each location."""
    _demands = data['demands']

    def demand_evaluator(manager, from_node):
        """Returns the demand of the current node"""
        return _demands[manager.IndexToNode(from_node)]

    return demand_evaluator


def create_volume_evaluator(data):
    """Creates callback to get demands at each location."""
    _demands = data['volumes']

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
        vehicle_capacity,
        vehicle_capacity,
        True,  # start cumul to zero
        capacity)

    # Add Slack for reseting to zero unload depot nodes.
    # e.g. vehicle with load 10/15 arrives at node 1 (depot unload)
    # so we have CumulVar = 10(current load) + -15(unload) + 5(slack) = 0.
    capacity_dimension = routing.GetDimensionOrDie(capacity)

    # Allow to drop reloading nodes with zero cost.
    for node in range(1, data['reloads']):
        node_index = manager.NodeToIndex(node)
        routing.AddDisjunction([node_index], 0)

    # Allow to drop regular node with a cost.
    for node in range(data['reloads'], len(data['demands'])):
        node_index = manager.NodeToIndex(node)
        capacity_dimension.SlackVar(node_index).SetValue(0)
        routing.AddDisjunction([node_index], 9999999999)


def add_volume_constraints(routing, manager, data, volume_evaluator_index):
    """Adds capacity constraint"""

    vehicle_volume = data['vehicle_cargo_volume']
    volume = 'Volume'
    routing.AddDimension(
        volume_evaluator_index,
        vehicle_volume,
        vehicle_volume,
        True,  # start cumul to zero
        volume)


def create_time_evaluator(data):
    """Creates callback to get total times between locations."""

    def service_time(data, node):
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
                    service_time(data, from_node) +
                    travel_time(data, from_node, to_node))

    def time_evaluator(manager, from_node, to_node):
        """Returns the total time between the two nodes"""
        return _total_time[manager.IndexToNode(from_node)][manager.IndexToNode(
            to_node)]

    return time_evaluator


def add_time_window_constraints(routing, manager, data, time_evaluator):
    """Add Time windows constraint"""
    time = 'Time'
    max_time = data['vehicle_max_time']
    routing.AddDimension(
        time_evaluator,
        max_time,  # allow waiting time
        max_time,  # maximum time per vehicle
        False,  # don't force start cumul to zero since we are giving TW to start nodes
        time)
    time_dimension = routing.GetDimensionOrDie(time)
    # Add time window constraints for each location except depot
    # and 'copy' the slack var in the solution object (aka Assignment) to print it
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == 0:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        routing.AddToAssignment(time_dimension.SlackVar(index))
    # Add time window constraints for each vehicle start node
    # and 'copy' the slack var in the solution object (aka Assignment) to print it
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['time_windows'][0][0],
                                                data['time_windows'][0][1])
        routing.AddToAssignment(time_dimension.SlackVar(index))
        # Warning: Slack var is not defined for vehicle's end node
        # routing.AddToAssignment(time_dimension.SlackVar(self.routing.End(vehicle_id)))


###########
# Printer #
###########
def print_solution(data, manager, routing, assignment):  # pylint:disable=too-many-locals
    """Prints assignment on console"""

    print(f'Objective: {assignment.ObjectiveValue()}')
    total_distance = 0
    total_load = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    volume_dimension = routing.GetDimensionOrDie('Volume')
    time_dimension = routing.GetDimensionOrDie('Time')
    dropped = []
    for order in range(data['reloads'], routing.nodes()):
        index = manager.NodeToIndex(order)
        if assignment.Value(routing.NextVar(index)) == index:
            dropped.append(order)
    print(f'dropped orders: {dropped}')
    dropped = []
    for reload in range(1, data['reloads']):
        index = manager.NodeToIndex(reload)
        if assignment.Value(routing.NextVar(index)) == index:
            dropped.append(reload)
    print(f'dropped reload stations: {dropped}')

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
    print('halo')
    dropped_orders = []
    for order in range(data['reloads'], routing.nodes()):
        index = manager.NodeToIndex(order)
        if assignment.Value(routing.NextVar(index)) == index:
            dropped_orders.append(order)

    dropped_without_depots = []
    for order in dropped_orders:
        dropped_order = order - data['reloads']
        dropped_without_depots.append(dropped_order)

    info['dropped_orders'] = dropped_without_depots

    total_distance = 0
    total_load = 0
    total_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
    volume_dimension = routing.GetDimensionOrDie('Volume')
    time_dimension = routing.GetDimensionOrDie('Time')
    info['route']= []
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        distance = 0
        while not routing.IsEnd(index):
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            distance += routing.GetArcCostForVehicle(previous_index, index,
                                                     vehicle_id)
            info['route'].append(manager.IndexToNode(index))
        load_var = capacity_dimension.CumulVar(index)
        time_var = time_dimension.CumulVar(index)
        total_distance += distance
        total_load += assignment.Min(load_var)
        total_time += assignment.Min(time_var)
    info['time'] = total_time
    info['distance'] = total_distance
    return info


########
# Main #
########
def solve(n: net.Net, timeout, solution_limit):
    """Entry point of the program"""
    # Instantiate the data problem.




    data = create_data_model(n)

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
        partial(create_demand_evaluator(data), manager))
    add_capacity_constraints(routing, manager, data, demand_evaluator_index)

    # Add volume constraint
    volume_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(create_volume_evaluator(data), manager))

    add_volume_constraints(routing, manager, data, volume_evaluator_index)

    # Add Time Window constraint
    time_evaluator_index = routing.RegisterTransitCallback(
        partial(create_time_evaluator(data), manager))
    add_time_window_constraints(routing, manager, data, time_evaluator_index)

    # Setting first solution heuristic (cheapest addition).
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)  # pylint: disable=no-member
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH)
    search_parameters.solution_limit = solution_limit
    # search_parameters.time_limit.FromSeconds(
    #     timeout)  # high time limit in order to accommodate for slow cpus or not having
    # enough solution to trigger solution_limit

    search_parameters.use_full_propagation = 1

    start_time = time.time()
    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)
    runtime = time.time() - start_time
    print(f'Solution time: {runtime}')

    info = {'solver_status': routing.status()}

    if solution:
        print_solution(data, manager, routing, solution)
        info = solution_info(data, manager, routing, solution, info)
        print(info)

    else:
        print("No solution found !")

    return info
