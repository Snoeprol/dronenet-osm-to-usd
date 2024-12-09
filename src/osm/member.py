class Member:
    """Represents a member in an OpenStreetMap relation.
    
    Members are references to nodes, ways, or other relations that are part of a relation.
    """
    def __init__(self, type: str, ref: int, role: str):
        self.type = type  # 'node', 'way', or 'relation'
        self.ref = ref    # ID reference to the member
        self.role = role  # Role of this member in the relation 