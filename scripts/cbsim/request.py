class Request:
    '''
        Request for delivery
    '''

    def __init__(self, weight=0, length = 0, width = 0, height = 0, orgn=None, dst=None):
        self.weight = weight # the request weight
        self.origin = orgn # node of origin
        self.destination = dst # node of destination
        self.length = length
        self.width = width
        self.height = height
        self.volume = self.length * self.width * self.height
    
    def __repr__(self):
        return '{0} -> {1}: {2}'.format(self.origin.nid, self.destination.nid, self.weight)
