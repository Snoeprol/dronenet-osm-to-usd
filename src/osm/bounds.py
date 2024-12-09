class Bounds:
    """Represents the bounding box in OpenStreetMap.
    
    Defines the geographic boundaries of the data.
    """
    def __init__(self, minlat: float, minlon: float, maxlat: float, maxlon: float, origin: str = None):
        self.minlat = minlat
        self.minlon = minlon
        self.maxlat = maxlat
        self.maxlon = maxlon
        self.origin = origin 