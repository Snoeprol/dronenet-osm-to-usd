class Way:
    """Represents a way in OpenStreetMap.
    
    A way is an ordered list of nodes that defines a linear feature or area.
    """
    def __init__(self, id: int, visible: bool = True, version: int = None, 
                 timestamp: str = None, changeset: int = None, uid: int = None, 
                 user: str = None):
        self.id = id
        self.visible = visible
        self.version = version
        self.timestamp = timestamp
        self.changeset = changeset
        self.uid = uid
        self.user = user
        self.nodes = []
        self.tags = [] 