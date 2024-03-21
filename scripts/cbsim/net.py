import math, random
import time
import numpy as np
import shapely

from scripts.cbsim.stochastic import Stochastic
from scripts.cbsim.node import Node
from scripts.cbsim.link import Link
from scripts.cbsim.region import Region
from scripts.cbsim.request import Request
from scripts.cbsim.route import Route


class Net:
    '''
        Delivery network as the graph model
    '''

    def __init__(self):
        # network geography
        self.nodes = []
        self.links = []
        self.regions = []
        # transport demand
        self.demand = []
        # shortest distances od_matrix
        self.sdm = np.array([[]])
        # matrix representation
        self.mtx = np.array([[]])
        self.bbox = None
        self.polygon = None
        self.vehicles = None

    def __repr__(self):
        res = "The network configuration:\n"
        for lnk in self.links:
            res += "{0} -> {1}: {2}\n".format(lnk.out_node.nid, \
                                              lnk.in_node.nid, \
                                              round(lnk.weight, 3))
        return res

    def contains_node(self, nid):
        '''
            Determines if the network contains a node with the specified id 
        '''
        for n in self.nodes:
            if n.nid == nid:
                return True
        return False

    def get_node(self, nid):
        '''
            Returns the first found node with the specified id
        '''
        for n in self.nodes:
            if n.nid == nid:
                return n
        return None

    def contains_region(self, code):
        '''
            Determines if the network contains a region with the specified code
        '''
        for region in self.regions:
            if region.code == code:
                return True
        return False

    def get_region(self, code):
        '''
            Returns the first found region with the specified code
        '''
        for region in self.regions:
            if region.code == code:
                return region
        return None

    def contains_link(self, out_node, in_node):
        '''
            Checks if the net contains a link
        '''
        for lnk in self.links:
            if lnk.out_node is out_node and lnk.in_node is in_node:
                return True
        return False

    def get_link(self, out_node, in_node):
        '''
            Returns the first found link with the specified out and in nodes
        '''
        for lnk in out_node.out_links:
            if lnk.out_node is out_node and lnk.in_node is in_node:
                return lnk
        return None

    def add_link(self, out_id, in_id, weight=0, directed=False):
        '''
            Adds a link with the specified characteristics
        '''
        if self.contains_node(out_id):
            # out-node is already in the net
            out_node = self.get_node(out_id)
            if self.contains_node(in_id):
                # in-node is already in the net
                in_node = self.get_node(in_id)
                if self.contains_link(out_node, in_node):
                    # out-node and in-node are already linked: change the link weight
                    self.get_link(out_node, in_node).weight = weight
                else:
                    # there is no such a link in the net: add a new one
                    new_link = Link(out_node, in_node, weight)
                    out_node.out_links.append(new_link)
                    in_node.in_links.append(new_link)
                    self.links.append(new_link)
            else:
                # the net contains the specified out-node, but there is no in-node with the specified id
                in_node = Node(in_id)
                new_link = Link(out_node, in_node, weight)
                out_node.out_links.append(new_link)
                in_node.in_links.append(new_link)
                self.nodes.append(in_node)
                self.links.append(new_link)
        else:
            # the net does not contain the specified out-node
            out_node = Node(out_id)
            if self.contains_node(in_id):
                # in-node is already in the net
                in_node = self.get_node(in_id)
            else:
                # there are no in-node and out-node with the specified ids
                in_node = Node(in_id)
                self.nodes.append(in_node)
            # create new link
            new_link = Link(out_node, in_node, weight)
            out_node.out_links.append(new_link)
            in_node.in_links.append(new_link)
            self.nodes.append(out_node)
            self.links.append(new_link)
        # add the reverse link
        if not directed:
            self.add_link(in_id, out_id, weight, True)

    @property
    def to_matrix(self):
        self.nodes.sort(key=lambda nd: nd.nid)  # sort the nodes!
        mtx = np.array([[np.inf for _ in self.nodes] for __ in self.nodes])
        for nd in self.nodes:
            mtx[nd.nid][nd.nid] = 0
        for lnk in self.links:
            mtx[lnk.out_node.nid][lnk.in_node.nid] = lnk.weight
        return mtx

    def floyd_warshall(self, nodes):
        nodes.sort(key=lambda nd: nd.nid)
        # print([nd.nid for nd in nodes])
        g = np.array([[np.inf for _ in nodes] for __ in nodes])
        for nd in nodes:
            g[nd.nid][nd.nid] = 0
        for lnk in self.links:
            g[lnk.out_node.nid][lnk.in_node.nid] = lnk.weight
        for nk in nodes:
            for ni in nodes:
                for nj in nodes:
                    dist = g[ni.nid][nk.nid] + g[nk.nid][nj.nid]
                    if g[ni.nid][nj.nid] > dist:
                        g[ni.nid][nj.nid] = dist
        return g

    def gps_distance(self, node1, node2):
        ''' 
            Haversine formula
        '''
        res = 0
        if (node1 is not None and node2 is not None):
            lat1, lon1 = node1.x, node1.y
            lat2, lon2 = node2.x, node2.y
            Earth_radius = 6371  # km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(0.5 * dlat) * math.sin(0.5 * dlat) + \
                 math.cos(math.radians(lat1)) * \
                 math.cos(math.radians(lat2)) * \
                 math.sin(0.5 * dlon) * math.sin(0.5 * dlon))
            res = round(2 * Earth_radius * \
                        math.atan2(math.sqrt(a), math.sqrt(1 - a)), 3)
        return res

    def gen_requests(self, sender=None, nodes=[], probs={}, s_weight=Stochastic(), s_dimensions=Stochastic()):
        # self.demand = []
        requests = []
        for node in nodes:
            if random.random() < probs[node.type]:
                rqst = Request(weight=round(s_weight.value()), length=round(s_dimensions.value()),
                               width=round(s_dimensions.value()), height=round(s_dimensions.value()), orgn=sender,
                               dst=node)
                requests.append(rqst)
        print("Demand generation for {} completed: {} requests generated.".format(sender,
                                                                                  len(requests)))
        self.demand.extend(requests)

    def gen_demand(self, flows, probs, requests=None, s_weight=None, traditional=False):
        '''
            Generates transport demand
            flows - incoming flows: {node_id: value}
            probs - probabilities of request depending on client's type: {type: prob}
            requests
            s_weight
            traditional - if True, uses traditioinal (zone-based) approach to generate demand
        '''

        clients = [nd for nd in self.nodes if nd.type != 'N' and nd.type != 'L']
        rcodes = [r.code for r in self.regions]
        _requests, reqs = [], []
        _total = sum(flows.values())  # total number of requests to generate
        _odm = np.matrix([
            [0 for r in self.regions]
            for f in flows
        ])
        _srf = np.matrix([
            [0.0 for r in self.regions]
            for f in flows
        ])
        _attrs = [[] for r in self.regions]

        # 1) generate set of _total requests with destinations according to provided probs
        if not requests:
            generated = 0
            while generated < _total:
                dst = random.choice(clients)
                if random.random() < probs[dst.type]:
                    req = Request(0, None, dst)
                    generated += 1
                    reqs.append(req)
        else:
            reqs = requests

        # 2) choose origin (inlet) according to provided flows

        # 2.1) define probabilities for origins to be assigned to the requests
        ps = {}  # { req: {inlet.nid: normalized(1/distance^2)} } probability
        # { rgn: {inlet.nid: normalized(1/distance^2)} } part of requests for traditional
        if traditional:
            # calculate attractions for the set of generated requests
            for req in reqs:
                idx = rcodes.index(req.destination.region.code)
                _attrs[idx].append(req)
            # print([len(a) for a in _attrs], sum([len(a) for a in _attrs]), 'attrs')
            # calculate space resistance function
            for f in flows.keys():
                for r in rcodes:
                    orgn = self.nodes[f]
                    dst = self.get_region(r)
                    i, j = list(flows.keys()).index(f), rcodes.index(r)
                    _srf[i, j] = 1 / self.gps_distance(orgn, dst) ** 2
                    # _srf[i, j] = 1.0
            # print(_srf)
            # calculate ODM by using gravitation model
            # denoms = [sum([len(_attrs[j]) * _srf[i, j] for j in range(len(self.regions))]) 
            #           for i in range(len(flows))]
            denoms = [sum([flows[list(flows.keys())[i]] * _srf[i, j] for i in range(len(flows))])
                      for j in range(len(self.regions))]
            # print(denoms)
            for f in flows.keys():
                for r in rcodes:
                    i, j = list(flows.keys()).index(f), rcodes.index(r)
                    _odm[i, j] = round(_srf[i, j] * len(_attrs[j]) * flows[f] / denoms[j])
            # print(_odm, _odm.sum())
            # print([_odm[i,:].sum() for i in range(_odm.shape[0])],
            #        sum([_odm[i,:].sum() for i in range(_odm.shape[0])]), 'prods')
            # print([_odm[:,i].sum() for i in range(_odm.shape[1])],
            #        sum([_odm[:,i].sum() for i in range(_odm.shape[1])]), 'attrs')
        else:
            for req in reqs:
                ds = {}
                dest = req.destination.closest_itsc
                for f in flows.keys():
                    orgn = self.nodes[f]
                    ds[f] = self.sdm[orgn.nid, dest.nid] + self.gps_distance(dest, req.destination)
                sum_p = sum([1 / d ** 2 for d in ds.values()])
                for f in ds.keys():
                    ds[f] = (1 / ds[f] ** 2) / sum_p
                ps[req] = ds

        # 2.2) assign origins
        if traditional:
            for f in flows.keys():
                for r in rcodes:
                    i, j = list(flows.keys()).index(f), rcodes.index(r)
                    assigned, empty = 0, len(_attrs[j]) == 0
                    while assigned < _odm[i, j] and not empty:
                        req = random.choice(_attrs[j])
                        _attrs[j].remove(req)
                        req.origin = self.get_node(f)
                        _requests.append(req)
                        assigned += 1
                        empty = len(_attrs[j]) == 0
                        # print(i, j, _odm[i, j], assigned)
        else:  # proposed
            for f in flows.keys():
                assigned = 0
                while assigned < flows[f]:
                    req = random.choice(reqs)
                    inlet_nid = self.roulette(ps[req])
                    if f == inlet_nid:
                        reqs.remove(req)
                        req.origin = self.get_node(f)
                        _requests.append(req)
                        assigned += 1

        # 2.3) generate consingment weight (for routing procedure)
        # TODO: depends on the client's type?
        for req in _requests:
            req.weight = s_weight.value()

        return _requests

    def roulette(self, probs):
        '''
            Select random key according to the probability (given as value)
            probs = {key: prob}, such that sum(probs.values()) == 1
            TODO: recalculate prob values to sum(values) == 1 (normalize probabilities)
        '''
        p, cums = 0, []
        for key in probs.keys():
            p += probs[key]
            cums.append(p)
        r = random.random()
        for i in range(len(cums)):
            if r < cums[i]:
                return list(probs.keys())[i]

    def dijkstra(self, source):
        '''
            Dijkstra's algorithm to calculate the shortest paths
            from the given source to all other nodes in the network
        '''
        size = len(self.nodes)
        distance = [np.inf for _ in range(size)]
        previous = [None for _ in range(size)]
        q = self.nodes[:]
        distance[source.nid] = 0
        while len(q) > 0:
            u = q[0]
            min_distance = distance[u.nid]
            for nd in q:
                if distance[nd.nid] < min_distance:
                    u = nd
                    min_distance = distance[u.nid]
            q.remove(u)
            neighbors = [lnk.in_node for lnk in u.out_links]
            for v in neighbors:
                alt = distance[u.nid] + self.get_link(u, v).weight
                if alt < distance[v.nid]:
                    distance[v.nid] = alt
                    previous[v.nid] = u
        return previous

    def define_path(self, source, target):
        '''
            Retrieve path defined by Dijkstra's algorithm
        '''
        previous = self.dijkstra(source)
        u = target
        path = []
        while previous[u.nid] is not None:
            path.append(u)
            u = previous[u.nid]
        path.reverse()
        return path

    def clarke_wright(self, sender_id=0, requests=[], capacity=0.15, verbose=True):
        '''
            Clarke-Wright (savings) algorithm to solve TSP
        '''

        def route_of(nd):
            for rt in routes:
                if nd in rt.nodes:
                    return rt
            return None

        def are_in_same_route(nd1, nd2):
            for rt in routes:
                if nd1 in rt.nodes and nd2 in rt.nodes:
                    return True
            return False

        def is_in_head(nd, rt):
            if rt is None or nd not in rt.nodes:
                return False
            return rt.nodes.index(nd) == 1

        def is_in_tail(nd, rt):
            if rt is None or nd not in rt.nodes:
                return False
            return rt.nodes.index(nd) == rt.size

        def is_head_or_tail(nd):
            rt = route_of(nd)
            return rt is not None and (is_in_head(nd, rt) or is_in_tail(nd, rt))

        routes = []  # the calculated routes
        n = len(self.nodes)  # number of nodes in the net

        # choose only requests with sender as origin
        sender = self.get_node(sender_id)  # sernder's node
        from_sender = []
        for rqst in requests:
            if rqst.origin is sender:
                from_sender.append(rqst)
        # combine multiple requests for the same destination
        if verbose: print("Combining multiple requests...")
        combined_weights = [0 for _ in range(n)]
        for rqst in from_sender:
            combined_weights[rqst.destination.nid] += rqst.weight
        combined = []  # set of requests combined by consignees
        consignee_ids = []
        for i in range(n):
            if combined_weights[i] > 0:
                combined.append(Request(combined_weights[i],
                                        sender, self.get_node(i)))
                consignee_ids.append(i)
        if verbose: print(sender_id, consignee_ids)
        # number of consignees
        m = len(consignee_ids)

        itsc_id = lambda nid: self.get_node(consignee_ids[nid]).closest_itsc.nid

        # get SDM for the routing problem
        d = np.array([[np.inf for _ in range(m + 1)]
                      for __ in range(m + 1)])
        d[0][0] = self.sdm[sender_id][sender_id]
        for i in range(1, m + 1):
            d[0][i] = self.sdm[sender_id][itsc_id(i - 1)]
            d[i][0] = self.sdm[itsc_id(i - 1)][sender_id]
            for j in range(1, m + 1):
                d[i][j] = self.sdm[itsc_id(i - 1)][itsc_id(j - 1)]
        if verbose:
            print("\nSDM for the routing problem:")
            print(d)

        if verbose: print("\nClarke-Wright algorithm started...")

        # forming the set of simple routes (pendular with empty returns)
        for rqst in combined:
            rt = Route(self, [rqst])
            routes.append(rt)
        # calculating the wins matrix
        if verbose: print("\nCalculating the wins matrix...")
        start_time = time.time()
        s = np.array([[0.0 for _ in range(m)]
                      for __ in range(m)])  # wins matrix
        for i in range(m):
            for j in range(m):
                if j < i:
                    s[i][j] = d[0][i] + d[0][j] - d[i][j]
                else:
                    s[i][j] = -np.inf
        if verbose:
            print("\nWins matrix for the routing problem (calculated in {} sec):".format(time.time() - start_time))
            print(s)
            print("\nForming the routes...")
        start_time = time.time()
        # start the routes merging
        while True:
            max_s = -np.inf
            i_max, j_max = 0, 0
            for i in range(m):
                for j in range(m):
                    if s[i][j] > max_s:
                        max_s = s[i][j]
                        i_max, j_max = i, j
            s[i_max][j_max] = -np.inf
            nd1, nd2 = self.get_node(itsc_id(i_max)), self.get_node(itsc_id(j_max))
            r1 = route_of(nd1)
            r2 = route_of(nd2)
            # conditions to be fulfilled for segments merging
            if not are_in_same_route(nd1, nd2) and \
                    is_head_or_tail(nd1) and is_head_or_tail(nd2) and \
                    r1.weight + r2.weight <= capacity:
                # checking the side before merging
                if r1.size > 1:
                    if is_in_tail(nd1, r1):
                        if r2.size > 1 and is_in_tail(nd2, r2):
                            r2.nodes.reverse()
                        r1.merge(r2)
                        routes.remove(r2)
                    else:
                        if r2.size > 1 and is_in_head(nd2, r2):
                            r2.nodes.reverse()
                        r2.merge(r1)
                        routes.remove(r1)
                else:
                    if is_in_tail(nd2, r2):
                        r2.merge(r1)
                        routes.remove(r1)
                    else:
                        r1.merge(r2)
                        routes.remove(r2)
            # checking if the optimization procedure is complete
            if max_s == -np.inf:
                break
        # printing the routes to console
        if verbose:
            print("{} routes were formed in {} sec.".format(len(routes), time.time() - start_time))
            for rt in routes:
                print(rt)
        # return the list of routes
        return routes

    @property
    def od_matrix(self):
        od = {}
        for origin in self.nodes:
            for destination in self.nodes:
                od[(origin.nid, destination.nid)] = 0
        for rqst in self.demand:
            od[(rqst.origin.nid, rqst.destination.nid)] += 1
        return od

    def load_from_file(self, fnodes='nodes.txt', flinks='links.txt', dlm='\t'):
        '''
            Load the net data (vertices and edges) from file
        '''
        # load nodes
        nodes = []
        f = open(fnodes, 'r')
        for data_line in f:
            data = data_line.split(dlm)
            node = Node(nid=int(data[0]), name=data[1])
            node.type = data[2].strip()
            node.x, node.y = float(data[3]), float(data[4])
            self.nodes.append(node)
            if node.type == 'N':
                reg_code = int(data[5])
                region = None
                if self.contains_region(reg_code):
                    region = self.get_region(reg_code)
                else:
                    reg_name = 'Zone ' + str(reg_code + 1)
                    region = Region(code=reg_code, name=reg_name)
                    self.regions.append(region)
                region.nodes.append(node)
                node.region = region
                node.inlet = data[6] == '1'
                node.outlet = data[7] == '1'
                nodes.append(node)
        f.close()
        self.set_regions()
        self.nodes.sort(key=lambda nd: nd.nid)
        # load links
        f = open(flinks, 'r')
        for data_line in f:
            data = data_line.split(dlm)
            nid1, nid2 = int(data[1]), int(data[2])
            dist = 0
            if self.contains_node(nid1) and self.contains_node(nid2):
                dist = self.gps_distance(self.get_node(nid1), self.get_node(nid2))
            self.add_link(nid1, nid2, dist)
        f.close()
        # set iternal variables
        self.mtx = self.to_matrix
        self.sdm = self.floyd_warshall(nodes)

    def auto_regions(self, inlets):
        self.regions = []  # reset
        # define zones - one per each inlet
        zones = list(range(len(inlets)))
        for z in zones:
            reg_name = 'Zone ' + str(z + 1)
            region = Region(code=z, name=reg_name)
            self.regions.append(region)
        #
        itscs = [node for node in self.nodes if node.type == 'N']  # intersections
        inodes = [self.get_node(inlet) for inlet in inlets]  # inlet nodes
        for itsc in itscs:
            # get closest inlet
            closest, dist = None, float('inf')
            for z in zones:
                d = self.gps_distance(inodes[z], itsc)  # get sdm distance?
                if d < dist:
                    dist = d
                    closest = z
            itsc.region = self.get_region(closest)

    def set_regions(self):
        itscs = [node for node in self.nodes if node.type == 'N']
        for node in self.nodes:
            closest, dist = node, float('inf')
            if not node in itscs:
                for itsc in itscs:
                    d = self.gps_distance(node, itsc)
                    if d < dist:
                        dist = d
                        closest = itsc
            node.closest_itsc = closest
            node.region = closest.region
            if not node in itscs:
                node.region.nodes.append(node)
        # define centroids
        for region in self.regions:
            if len(region.nodes) > 0:
                x, y = 0.0, 0.0
                for nd in region.nodes:
                    x += nd.x
                    y += nd.y
                region.x = x / len(region.nodes)
                region.y = y / len(region.nodes)
        # sort by code
        self.regions.sort(key=lambda r: r.code)

    def simulate(self, requests=[], outlets=None, loadpoints=None, capacity=0.15):

        def distances(rs, toloadpoint=False):
            ds = []
            if toloadpoint:  # deliveries to loadpoints only
                # get loadpoint nodes
                lps = []  # loadpoint nodes
                for loadpoint in loadpoints:
                    lp = self.get_node(loadpoint)
                    if lp is not None:
                        lps.append(lp)
                # determine distance to closest loadpoints (direct and back)
                for req in rs:
                    # choose the closest loadpoint
                    lds = {}
                    for lp in lps:
                        lcl = self.gps_distance(lp.closest_itsc, lp)
                        ld = self.sdm[req.origin.closest_itsc.nid][lp.closest_itsc.nid]
                        lds[lp] = 2 * lcl + ld
                    closest = min(lds, key=lds.get)
                    direct = lds[closest]
                    # choose the closest outlet
                    outds = []
                    for outlet in outlets:
                        outnode = self.get_node(outlet)
                        if outnode is not None:
                            outds.append(self.sdm[closest.closest_itsc.nid][outnode.closest_itsc.nid])
                    back = min(outds) if len(outds) > 0 else 0
                    ds.append(direct + back)
                    # print(closest, direct, back)
            else:  # deliveries to clients
                for req in rs:
                    # distance from the closest intersection to client
                    dcl = self.gps_distance(req.destination.closest_itsc, req.destination)
                    # distance from entry to the client's closest intersection
                    direct = self.sdm[req.origin.closest_itsc.nid][req.destination.closest_itsc.nid]
                    # choose the closest outlet
                    outds = []
                    for outlet in outlets:
                        outnode = self.get_node(outlet)
                        if outnode is not None:
                            outds.append(self.sdm[req.destination.closest_itsc.nid][outnode.closest_itsc.nid])
                    back = min(outds) if len(outds) > 0 else 0
                    ds.append(direct + 2 * dcl + back)
                    # print(direct, dcl, back)
            return ds

        reqs = requests[:]
        breqs, dreqs = [], []

        if loadpoints is not None:  # if bikes are used as alternative mode of transport
            # select requests to be delivered not by bikes
            for req in reqs:
                if req.weight < capacity:
                    breqs.append(req)
                else:
                    dreqs.append(req)
            return distances(dreqs), distances(breqs, toloadpoint=True)
        else:
            # deliveries only by conventional vehicles
            return distances(reqs), []

    def set_closest_itsc(self):
        itscs = [node for node in self.nodes if node.type == 'N']
        for node in self.nodes:
            closest, dist = node, float('inf')
            if not node in itscs:
                for itsc in itscs:
                    d = self.gps_distance(node, itsc)
                    if d < dist:
                        dist = d
                        closest = itsc
                node.closest_itsc = closest


class AreaBoundingBox:
    def __init__(self, longitude_west: float, longitude_east: float, latitude_south: float, latitude_north: float):
        self.longitude_west: float = longitude_west
        self.longitude_east: float = longitude_east
        self.latitude_south: float = latitude_south
        self.latitude_north: float = latitude_north

    def __str__(self):  # should be "(lat_south,long_west,lat_north,long_east)"
        return f"({self.latitude_south},{self.longitude_west},{self.latitude_north},{self.longitude_east})"

    def tuple_bbox(self):
        return self.latitude_north, self.latitude_south, self.longitude_east, self.longitude_west

    def convert_to_polygon_points(self):
        points = ((self.longitude_west, self.latitude_north),
                  (self.longitude_east, self.latitude_north),
                  (self.longitude_east, self.latitude_south),
                  (self.longitude_west, self.latitude_south))
        return points


class AreaBoundingPolygon:
    def __init__(self, coordinates: tuple):
        self.points: tuple = coordinates  # ((long, lat),(...))
        self.geometry = shapely.geometry.Polygon(self.points)

    def create_osm_area(self):
        # 'poly: "50.0661 19.9361 50.0655 19.9419 50.0644 19.9447 50.0609 19.9436 50.0587 19.9406\
        #                50.0546 19.9389 50.0555 19.9375 50.0557 19.9352 50.0589 19.9334 50.0619 19.9319"'
        string = 'poly: "'
        for point in self.points:
            string += '{:.4f}'.format(round(point[1], 4))
            string += ' '
            string += '{:.4f}'.format(round(point[0], 4))
            string += ' '

        string = string[:-1]
        string += '"'

        return string
