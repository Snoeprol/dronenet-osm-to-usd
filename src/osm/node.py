class Node:
    """Represents a node in OpenStreetMap.
    
    A node represents a specific point on the earth's surface defined by its latitude and longitude.
    """
    def __init__(self, id: int, lat: float, lon: float, visible: bool = True,
                 version: int = None, timestamp: str = None, 
                 changeset: int = None, uid: int = None, user: str = None):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.visible = visible
        self.version = version
        self.timestamp = timestamp
        self.changeset = changeset
        self.uid = uid
        self.user = user
        self.tags = [] 