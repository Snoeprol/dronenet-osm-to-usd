from src.osm.osm import OSM
import os
import matplotlib.pyplot as plt
import numpy as np
from numba import njit
from typing import List, Tuple

@njit
def process_nodes(node_lons: np.ndarray, node_lats: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Process nodes using Numba for faster computation."""
    return node_lons, node_lats

@njit
def find_node_by_id(node_ids: np.ndarray, node_lons: np.ndarray, 
                    node_lats: np.ndarray, search_id: int) -> Tuple[float, float]:
    """Find node coordinates by ID using Numba."""
    idx = np.where(node_ids == search_id)[0]
    if len(idx) > 0:
        return node_lons[idx[0]], node_lats[idx[0]]
    return np.nan, np.nan

def process_way(way_node_refs: List[int], node_ids: np.ndarray, 
               node_lons: np.ndarray, node_lats: np.ndarray) -> Tuple[List[float], List[float]]:
    """Process a single way's nodes."""
    way_lons = []
    way_lats = []
    
    for node_ref in way_node_refs:
        lon, lat = find_node_by_id(node_ids, node_lons, node_lats, node_ref)
        if not np.isnan(lon):
            way_lons.append(lon)
            way_lats.append(lat)
    
    return way_lons, way_lats

def visualize_osm(osm: OSM):
    """Create a simple 2D visualization of the OSM data with Numba optimization."""
    plt.figure(figsize=(12, 8))
    
    # Convert node data to numpy arrays for faster processing
    visible_nodes = [node for node in osm.nodes if node.visible]
    node_ids = np.array([node.id for node in visible_nodes])
    node_lons = np.array([node.lon for node in visible_nodes])
    node_lats = np.array([node.lat for node in visible_nodes])
    
    # Process nodes using Numba
    node_lons, node_lats = process_nodes(node_lons, node_lats)
    
    # Plot nodes
    plt.scatter(node_lons, node_lats, c='blue', s=10, alpha=0.6, label='Nodes')
    
    # Process and plot ways
    visible_ways = [way for way in osm.ways if way.visible]
    for way in visible_ways:
        if way.nodes:
            way_lons, way_lats = process_way(way.nodes, node_ids, node_lons, node_lats)
            if way_lons and way_lats:
                plt.plot(way_lons, way_lats, 'r-', linewidth=1, alpha=0.5)
    
    # Set labels and title
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('OSM Data Visualization')
    plt.legend()
    plt.grid(True)
    
    # Make the plot look more map-like with equal aspect ratio
    plt.axis('equal')
    
    return plt

def visualize_land(osm: OSM):
    """Create a visualization of just the land boundaries."""
    plt.figure(figsize=(12, 8))
    
    # Convert node data to numpy arrays for faster processing
    visible_nodes = [node for node in osm.nodes if node.visible]
    node_ids = np.array([node.id for node in visible_nodes])
    node_lons = np.array([node.lon for node in visible_nodes])
    node_lats = np.array([node.lat for node in visible_nodes])
    
    # Find ways that represent land
    land_ways = []
    for way in osm.ways:
        if not way.visible:
            continue
            
        is_land = False
        for tag in way.tags:
            # More specific land-related tags
            if (
                # Coastline is the most reliable indicator of land boundaries
                (tag.key == 'natural' and tag.value == 'coastline') or
                # Specific landuse tags that definitely indicate land
                (tag.key == 'landuse' and tag.value in [
                    'residential', 'forest', 'farmland', 'grass',
                    'meadow', 'industrial', 'commercial'
                ]) or
                # Natural land features
                (tag.key == 'natural' and tag.value in [
                    'land', 'wood', 'scrub', 'heath', 'grassland'
                ])
            ):
                is_land = True
                break
            
            # Exclude water features explicitly
            if (
                (tag.key == 'natural' and tag.value in ['water', 'bay', 'strait']) or
                (tag.key == 'waterway') or
                (tag.key == 'water')
            ):
                is_land = False
                break
        
        if is_land:
            land_ways.append(way)
    
    # Plot land boundaries
    for way in land_ways:
        if way.nodes:
            way_lons, way_lats = process_way(way.nodes, node_ids, node_lons, node_lats)
            if way_lons and way_lats:
                # Close the polygon if it's not closed
                if way_lons[0] != way_lons[-1] or way_lats[0] != way_lats[-1]:
                    way_lons.append(way_lons[0])
                    way_lats.append(way_lats[0])
                plt.fill(way_lons, way_lats, 'lightgreen', alpha=0.3, edgecolor='darkgreen', linewidth=0.5)
    
    # Set labels and title
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('OSM Land Areas')
    plt.grid(True)
    
    # Make the plot look more map-like with equal aspect ratio
    plt.axis('equal')
    
    # If bounds exist, use them to set the plot limits
    if osm.bounds:
        plt.xlim(osm.bounds.minlon, osm.bounds.maxlon)
        plt.ylim(osm.bounds.minlat, osm.bounds.maxlat)
    
    return plt

def main():
    # Get the absolute path to samples/map.osm
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sample_path = os.path.join(current_dir, 'samples', 'map.osm')
    
    # Parse the OSM file
    osm = OSM.from_xml(sample_path)
    
    # Only show land visualization
    plt = visualize_land(osm)
    plt.show()

if __name__ == "__main__":
    main()
