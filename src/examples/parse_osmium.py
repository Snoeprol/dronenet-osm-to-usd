import osmium
import os
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Set
from collections import defaultdict

class LandHandler(osmium.SimpleHandler):
    def __init__(self):
        super(LandHandler, self).__init__()
        self.nodes: Dict[int, tuple] = {}  # id -> (lon, lat)
        self.land_ways: List[List[int]] = []  # list of node id lists
        self.land_tags: Set[str] = set()
        self.crossing_ways: List[tuple] = []  # [(way_id, tags, nodes)]
        
        # Define the area of interest
        self.min_lon = 4.78575
        self.max_lon = 4.78775
        self.min_lat = 52.96
        self.max_lat = 52.96 + 0.005  # Using average of 0.0056 and 0.0044
        
    def node(self, n):
        """Save all nodes with their coordinates."""
        self.nodes[n.id] = (n.location.lon, n.location.lat)
    
    def way(self, w):
        """Process ways and check if they cross our area of interest."""
        # Get coordinates for the way
        coords = []
        for n in w.nodes:
            if n.ref in self.nodes:
                coords.append(self.nodes[n.ref])
        
        if not coords:
            return
            
        # Check if way crosses our area
        lons, lats = zip(*coords)
        if (min(lons) <= self.max_lon and max(lons) >= self.min_lon and
            min(lats) <= self.max_lat and max(lats) >= self.min_lat):
            # Store the crossing way with its tags
            tags = [(tag.k, tag.v) for tag in w.tags]
            nodes = [n.ref for n in w.nodes]
            self.crossing_ways.append((w.id, tags, nodes))

def analyze_crossing_objects(osm_path: str):
    """Analyze objects crossing the specified area."""
    handler = LandHandler()
    handler.apply_file(osm_path)
    
    print("\nObjects crossing the specified area:")
    print(f"Area bounds: Lon({handler.min_lon}, {handler.max_lon}), Lat({handler.min_lat}, {handler.max_lat})")
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Plot the area of interest
    plt.axvline(x=handler.min_lon, color='r', linestyle='--', alpha=0.5, label='Area of Interest')
    plt.axvline(x=handler.max_lon, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y=handler.min_lat, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y=handler.max_lat, color='r', linestyle='--', alpha=0.5)
    
    # Plot crossing ways with different colors and annotations
    colors = plt.cm.tab20(np.linspace(0, 1, len(handler.crossing_ways)))
    
    for (way_id, tags, nodes), color in zip(handler.crossing_ways, colors):
        coords = []
        for node_id in nodes:
            if node_id in handler.nodes:
                coords.append(handler.nodes[node_id])
        
        if coords:
            lons, lats = zip(*coords)
            line = plt.plot(lons, lats, '-', linewidth=2, alpha=0.7, color=color, 
                          label=f'Way {way_id}')[0]
            
            # Calculate center point for annotation
            center_lon = np.mean(lons)
            center_lat = np.mean(lats)
            
            # Create annotation text
            annotation = f"Way {way_id}\n"
            for k, v in tags:
                annotation += f"{k}={v}\n"
            
            # Add annotation with arrow pointing to the line
            plt.annotate(annotation, 
                        xy=(center_lon, center_lat),
                        xytext=(center_lon + 0.0005, center_lat + 0.0005),
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                        arrowprops=dict(arrowstyle="->"))
            
            # Print detailed information
            print(f"\nWay {way_id}:")
            print("Properties:")
            for k, v in tags:
                print(f"  {k} = {v}")
            print("Nodes:")
            for node_id in nodes:
                if node_id in handler.nodes:
                    lon, lat = handler.nodes[node_id]
                    print(f"  Node {node_id}: ({lon:.6f}, {lat:.6f})")
    
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Objects Crossing Specified Area with Properties')
    plt.grid(True)
    plt.axis('equal')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Adjust layout to prevent annotation cutoff
    plt.tight_layout()
    
    return plt

def main():
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sample_path = os.path.join(current_dir, 'samples', 'map.osm')
    
    # Analyze crossing objects
    plt = analyze_crossing_objects(sample_path)
    plt.show()

if __name__ == "__main__":
    main() 