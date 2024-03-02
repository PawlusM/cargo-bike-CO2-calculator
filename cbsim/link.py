from cbsim.node import Node

class Link:
    '''
        Link between the net of nodes 
        Attributes: out node <Node>, in node <Node>, weight <float>
        Method: repr
    ''' 
    
    def __init__(self, out_node=None, in_node=None, weight=0):
        # type: (Node, Node, float) -> Link
        self.out_node = out_node
        self.in_node = in_node
        # link length [km]
        self.weight = weight
    
    def __repr__(self):
        return "{} -> {}: {}".format(self.out_node.name, self.in_node.name, self.weight)
