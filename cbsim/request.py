class Request:
    '''
        Request for delivery
    '''

    def __init__(self, weight=0, orgn=None, dst=None):
        self.weight = weight # the request weight
        self.origin = orgn # node of origin
        self.destination = dst # node of destination
    
    def __repr__(self):
        return '{0} -> {1}: {2}'.format(self.origin.nid, self.destination.nid, self.weight)
