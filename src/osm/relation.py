class Relation:
    """Represents a relation in OpenStreetMap.
    
    A relation is a group of elements (nodes, ways, and/or other relations) that define a logical or geographic relationship.
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
        self.members = []
        self.tags = [] 