class Region:
    '''
        Transport analysis zone
    '''
    
    def __init__(self, code=0, name='TAZ'):
        self.code = code
        self.name = name
        # location of the centroid
        self.x = 0
        self.y = 0
        # nodes inside the region
        self.nodes = []
    
    def __repr__(self):
        return "{}: [{}, {}], {} nodes".format(self.name, self.x, self.y, len(self.nodes))