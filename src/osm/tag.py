class Tag:
    """Represents a tag in OpenStreetMap.
    
    Tags are key-value pairs that store metadata about map features.
    """
    def __init__(self, k: str, v: str):
        self.key = k
        self.value = v 