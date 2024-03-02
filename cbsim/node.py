class Node:
    '''
        Node of the transport net
    ''' 

    def __init__(self, nid=0, name='Node'):
        self.nid = nid
        self.name = 'Node' + str(nid) if name == 'Node' else name
        # graph features
        self.out_links = []
        self.in_links = []
        # demand parameters
        self.s_weight = None # stochastic
        self.req_prob = 1
        self.requested = False
        # location (coordinates)
        self.x = 0
        self.y = 0
        # type
        self.type = 'notype'
        # communication region
        self.region = None
        # the closest intersection (for non-intersection nodes only)
        self.closest_itsc = None
        # inlet and outlet functions (for intersection node only)
        self.inlet = False
        self.outlet = False
    
    def __repr__(self):
        return "{}: [{}, {}], {}".format(self.name, self.x, self.y, self.type)
