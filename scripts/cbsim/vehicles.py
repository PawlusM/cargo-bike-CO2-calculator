class Vehicles:
    '''
    Vehicle fleet
    '''

    def __init__(self, vehicle_data):
        self.count = 0
        self.capacity = vehicle_data["vehicle_capacity"]
        self.cargo_length = vehicle_data["cargo_length"]
        self.cargo_width = vehicle_data["cargo_width"]
        self.cargo_height = vehicle_data["cargo_height"]
        self.cargo_volume = self.cargo_length * self.cargo_width * self.cargo_height

    def __repr__(self):
        return f"Vehicles count:({self.count}, vehicle capacity:{self.capacity}, vehicle volume:{self.cargo_volume})"
