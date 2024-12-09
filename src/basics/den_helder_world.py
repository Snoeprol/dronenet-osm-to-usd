import json
import os
from typing import List, Dict, Set
from collections import defaultdict
from pxr import Usd, UsdGeom, Gf, Sdf, UsdShade
import xml.etree.ElementTree as ET
import osmium
import shapely.wkb as wkblib
from PIL import Image
import math
import requests
from io import BytesIO
from src.examples.map import deg2num

class JsonHandler:
    def __init__(self):
        self.nodes: Dict[int, tuple] = {}  # id -> (lon, lat)
        self.ways: List[tuple] = []  # [(way_id, tags, nodes)]
        self.water_features = []  # Store water features as (coords, tags)
        self.land_features = []   # Store land features as (coords, tags)
        self.roads = []          # Store road features as (coords, tags, width)
        
        # Define the area of interest with the new coordinates
        self.min_lat = 52.94853  # Updated
        self.max_lat = 52.96715  # Updated
        self.min_lon = 4.77914   # Updated
        self.max_lon = 4.80407   # Updated
        
        # Constants for scaling and heights
        self.SCALE = 2000        # Base scale for the map
        self.HEIGHT_SCALE = 0.02 # Height scale for buildings
        
        # Add surface-specific constants
        self.SURFACE_SCALE = 10  # Scale factor for the surface size
        self.SURFACE_HEIGHT = -0.1  # Height offset for the surface
        
        # Store all coordinates to calculate center later
        self.all_coords = []

    def add_coordinates(self, coords):
        """Add coordinates to tracking list for center calculation"""
        self.all_coords.extend(coords)

    def transform_coordinates(self, coords, center_lon, center_lat):
        """Transform lon/lat coordinates to local space"""
        return [
            ((lon - center_lon) * self.SCALE, 
             (lat - center_lat) * self.SCALE)
            for lon, lat in coords
        ]

    def process_json(self, json_data: dict):
        """Process the JSON data."""
        print(f"Total elements in JSON: {len(json_data['elements'])}")
        
        # First pass: collect all nodes
        for element in json_data['elements']:
            if element['type'] == 'node':
                if 'lon' in element and 'lat' in element:
                    coords = (element['lon'], element['lat'])
                    self.nodes[element['id']] = coords
                    self.add_coordinates([coords])
        
        # Second pass: collect all ways and classify them
        for element in json_data['elements']:
            if element['type'] == 'way':
                tags = element.get('tags', {})
                if 'building' in tags:
                    self.process_way(element)
                elif 'natural' in tags or 'water' in tags:
                    self.classify_feature(element)

    def classify_feature(self, way: dict):
        """Classify way as water or land feature."""
        # Get nodes from way
        coords = []
        nodes = way.get('nodes', [])
        
        # Handle both node IDs and direct coordinate pairs
        for node in nodes:
            if isinstance(node, (int, str)):  # If node is an ID
                if node in self.nodes:
                    coords.append(self.nodes[node])
            elif isinstance(node, (tuple, list)):  # If node is already coordinates
                coords.append(node)
            elif hasattr(node, 'ref'):  # If node is an osmium Node object
                if node.ref in self.nodes:
                    coords.append(self.nodes[node.ref])
        
        if not coords:
            return

        # Check if way crosses our area of interest
        lons, lats = zip(*coords)
        if not (min(lons) <= self.max_lon and max(lons) >= self.min_lon and
                min(lats) <= self.max_lat and max(lats) >= self.min_lat):
            return  # Skip if not in our area

        tags = way.get('tags', {})
        if isinstance(tags, (osmium.osm.TagList)):  # Handle osmium TagList objects
            tags = {tag.k: tag.v for tag in tags}
        
        # Water features
        is_water = False
        if ('natural' in tags and tags['natural'] == 'water') or \
           ('water' in tags) or \
           ('waterway' in tags):
            self.water_features.append((coords, tags))
            is_water = True
        
        # Land features (if not water)
        if not is_water:
            land_types = {
                'natural': ['wood', 'grassland', 'heath', 'scrub', 'forest', 'beach'],
                'landuse': ['forest', 'grass', 'meadow', 'recreation_ground', 'park'],
                'leisure': ['park', 'garden', 'nature_reserve'],
            }
            
            for key, values in land_types.items():
                if key in tags and tags[key] in values:
                    self.land_features.append((coords, tags))
                    break

    def create_ground_plane(self, stage, center_lon, center_lat):
        """Create a textured ground plane using OSM map tiles."""
        surface = UsdGeom.Mesh.Define(stage, '/World/Surface')
        
        # Download map tiles for the area
        print("Downloading map tiles for ground texture...")
        print(f"Area bounds: lat({self.min_lat}, {self.max_lat}), lon({self.min_lon}, {self.max_lon})")
        image = self.fetch_tiles(self.min_lat, self.max_lat, self.min_lon, self.max_lon, zoom=17)
        
        if image:
            # Save the image
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(current_dir, 'output')
            image_path = os.path.join(output_dir, 'ground_texture.png')
            image.save(image_path)
            print(f"Ground texture saved to: {image_path}")
            
            # Calculate the size based on the actual area covered
            # Convert lat/lon differences to meters using the scale factor
            width = (self.max_lon - self.min_lon) * self.SCALE
            height = (self.max_lat - self.min_lat) * self.SCALE
            
            # Define the vertices for a flat rectangular surface
            # Center the surface at (0,0,0)
            half_width = width / 2
            half_height = height / 2
            points = [
                Gf.Vec3f(-half_width, -0.1, -half_height),  # Bottom-left
                Gf.Vec3f(half_width, -0.1, -half_height),   # Bottom-right
                Gf.Vec3f(half_width, -0.1, half_height),    # Top-right
                Gf.Vec3f(-half_width, -0.1, half_height),   # Top-left
            ]
            
            # Define face connections
            face_vertex_counts = [4]  # One face with 4 vertices
            face_vertex_indices = [0, 1, 2, 3]  # Connect vertices in counter-clockwise order
            
            # Set the mesh attributes
            surface.CreatePointsAttr(points)
            surface.CreateFaceVertexCountsAttr(face_vertex_counts)
            surface.CreateFaceVertexIndicesAttr(face_vertex_indices)
            
            # Add texture coordinates through primvars
            texCoords = UsdGeom.PrimvarsAPI(surface).CreatePrimvar(
                "st",
                Sdf.ValueTypeNames.TexCoord2fArray,
                UsdGeom.Tokens.varying
            )
            
            # Set UV coordinates for the surface - flipped vertically
            texCoords.Set([
                (0, 1),  # Bottom-left (was 0,0)
                (1, 1),  # Bottom-right (was 1,0)
                (1, 0),  # Top-right (was 1,1)
                (0, 0),  # Top-left (was 0,1)
            ])
            
            # Create material
            material = UsdShade.Material.Define(stage, '/World/Surface/Material')
            
            # Create PBR shader
            pbrShader = UsdShade.Shader.Define(stage, '/World/Surface/Material/PBRShader')
            pbrShader.CreateIdAttr("UsdPreviewSurface")
            
            # Create primvar reader for UV coordinates
            stReader = UsdShade.Shader.Define(stage, '/World/Surface/Material/stReader')
            stReader.CreateIdAttr("UsdPrimvarReader_float2")
            stReader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
            
            # Create texture sampler
            diffuseTexture = UsdShade.Shader.Define(stage, '/World/Surface/Material/diffuseTexture')
            diffuseTexture.CreateIdAttr("UsdUVTexture")
            
            # Set the texture file path
            diffuseTexture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(image_path)
            
            # Connect texture coordinates to the texture sampler
            diffuseTexture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
                stReader.ConnectableAPI(), "result"
            )
            
            # Connect texture to shader's diffuse color
            pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                diffuseTexture.ConnectableAPI(), "rgb"
            )
            
            # Connect shader to material
            material.CreateSurfaceOutput().ConnectToSource(
                pbrShader.ConnectableAPI(), "surface"
            )
            
            # Bind material to surface
            UsdShade.MaterialBindingAPI(surface).Bind(material)
        else:
            print("Failed to create ground texture")

    def create_water_feature(self, stage, coords, tags):
        """Create a water feature mesh using transformed coordinates."""
        water_path = f'/World/Water/water_{len(self.water_features)}'
        water = UsdGeom.Mesh.Define(stage, water_path)
        
        # Create points for water surface (slightly below ground)
        points = []
        for x, z in coords:
            points.append(Gf.Vec3f(x, -0.05, z))
        
        # Create face indices for a single polygon
        face_indices = list(range(len(points)))
        vertex_counts = [len(points)]  # One face with all vertices
        
        water.CreatePointsAttr(points)
        water.CreateFaceVertexIndicesAttr(face_indices)
        water.CreateFaceVertexCountsAttr(vertex_counts)
        
        # Create blue material for water
        material = UsdShade.Material.Define(stage, f'{water_path}/material')
        shader = UsdShade.Shader.Define(stage, f'{water_path}/material/PBRShader')
        shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set((0.1, 0.3, 0.8))  # Brighter blue
        shader.CreateInput('opacity', Sdf.ValueTypeNames.Float).Set(0.9)  # More opaque
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.1)
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.2)  # Make it shiny
        UsdShade.MaterialBindingAPI(water).Bind(material)

    def create_land_feature(self, stage, coords, tags):
        """Create a land feature mesh using transformed coordinates."""
        land_path = f'/World/Land/land_{len(self.land_features)}'
        land = UsdGeom.Mesh.Define(stage, land_path)
        
        # Create points slightly above ground
        points = []
        for x, z in coords:
            points.append(Gf.Vec3f(x, 0.02, z))
        
        # Create face indices for a single polygon
        face_indices = list(range(len(points)))
        vertex_counts = [len(points)]
        
        land.CreatePointsAttr(points)
        land.CreateFaceVertexIndicesAttr(face_indices)
        land.CreateFaceVertexCountsAttr(vertex_counts)
        
        # Create material based on land type
        material = UsdShade.Material.Define(stage, f'{land_path}/material')
        shader = UsdShade.Shader.Define(stage, f'{land_path}/material/PBRShader')
        shader.CreateIdAttr('UsdPreviewSurface')
        
        # Different colors for different land types
        land_colors = {
            'forest': (0.2, 0.5, 0.2),  # Dark green
            'grass': (0.3, 0.6, 0.3),   # Medium green
            'park': (0.4, 0.7, 0.4),    # Light green
            'beach': (0.9, 0.9, 0.7),   # Sand color
            'recreation_ground': (0.5, 0.7, 0.5)  # Pale green
        }
        
        land_type = next((v for k, v in tags.items() if k in ['natural', 'landuse', 'leisure']), 'grass')
        color = land_colors.get(land_type, (0.4, 0.6, 0.4))  # Default green
        
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(color)
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.8)
        UsdShade.MaterialBindingAPI(land).Bind(material)

    def process_way(self, way: dict):
        """Process and store way data."""
        coords = []
        for node_id in way.get('nodes', []):
            if node_id in self.nodes:
                coords.append(self.nodes[node_id])
        
        if coords:
            tags = dict(way.get('tags', {}))
            self.ways.append((way['id'], tags, way['nodes']))
            # Add coordinates for center calculation
            self.add_coordinates(coords)

    def get_height(self, tags: dict) -> float:
        """Extract height information from tags."""
        # Try different tags for height information
        if 'height' in tags:
            try:
                return float(tags['height'])
            except ValueError:
                pass
        
        if 'building:levels' in tags:
            try:
                # Assume each level is roughly 2.8 meters (more realistic)
                return float(tags['building:levels']) * 2.8
            except ValueError:
                pass
        
        # Default heights based on building type (more conservative values)
        if 'building' in tags:
            building_type = tags['building']
            default_heights = {
                'hotel': 12,
                'apartments': 9,
                'house': 5,
                'yes': 4,
                'commercial': 6,
                'industrial': 8
            }
            return default_heights.get(building_type, 4)  # default to 4m
        
        return 2.5  # Lower default height

    def process_road(self, road: dict):
        """Process and store road data."""
        if not road['nodes']:
            return
            
        road_type = road['tags'].get('highway', 'unknown')
        amenity = road['tags'].get('amenity', '')
        
        # Different widths for different road types
        road_widths = {
            'motorway': 8,
            'trunk': 7,
            'primary': 6,
            'secondary': 5,
            'tertiary': 4,
            'residential': 3,
            'service': 2,
            'footway': 1,
            'path': 0.5,
            'parking_space': 2.5,  # Added width for parking spaces
            'unknown': 3
        }
        
        # Handle parking spaces
        if amenity == 'parking_space':
            width = road_widths['parking_space']
            self.roads.append((road['nodes'], road['tags'], width))
            return
        
        width = road_widths.get(road_type, 3)
        self.roads.append((road['nodes'], road['tags'], width))

    def create_road(self, stage, coords, width, tags):
        """Create a road mesh using transformed coordinates."""
        road_path = f'/World/Roads/road_{len(self.roads)}'
        road = UsdGeom.Mesh.Define(stage, road_path)
        
        height = 0.02 if tags.get('amenity') == 'parking_space' else 0.01
        
        # Create points using transformed coordinates
        points = []
        for x, z in coords:
            points.append(Gf.Vec3f(x, height, z))
        
        # Create road surface with width
        road_points = []
        road_indices = []
        vertex_counts = []
        
        # Create road segments
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # Calculate perpendicular vector for width
            dx = p2[0] - p1[0]
            dz = p2[2] - p1[2]
            length = (dx * dx + dz * dz) ** 0.5
            if length > 0:
                nx = -dz * width / length
                nz = dx * width / length
                
                # Create four corners of road segment
                road_points.extend([
                    Gf.Vec3f(p1[0] - nx, height, p1[2] - nz),
                    Gf.Vec3f(p1[0] + nx, height, p1[2] + nz),
                    Gf.Vec3f(p2[0] + nx, height, p2[2] + nz),
                    Gf.Vec3f(p2[0] - nx, height, p2[2] - nz)
                ])
                
                # Create face indices
                base = i * 4
                road_indices.extend([base, base + 1, base + 2, base + 3])
                vertex_counts.append(4)
        
        road.CreatePointsAttr(road_points)
        road.CreateFaceVertexIndicesAttr(road_indices)
        road.CreateFaceVertexCountsAttr(vertex_counts)
        
        # Create material for road
        material = UsdShade.Material.Define(stage, f'{road_path}/material')
        shader = UsdShade.Shader.Define(stage, f'{road_path}/material/PBRShader')
        shader.CreateIdAttr('UsdPreviewSurface')
        
        # Different colors for different road types
        road_type = tags.get('highway', 'unknown')
        amenity = tags.get('amenity', '')
        road_colors = {
            'motorway': (0.3, 0.3, 0.3),  # Dark gray
            'trunk': (0.35, 0.35, 0.35),
            'primary': (0.4, 0.4, 0.4),
            'secondary': (0.45, 0.45, 0.45),
            'residential': (0.5, 0.5, 0.5),  # Light gray
            'footway': (0.6, 0.6, 0.5),  # Tan
            'path': (0.7, 0.7, 0.6),  # Light tan
            'parking_space': (0.4, 0.4, 0.5),  # Bluish gray for parking
        }
        
        # Use parking space color if it's a parking amenity
        if amenity == 'parking_space':
            color = road_colors['parking_space']
        else:
            color = road_colors.get(road_type, (0.5, 0.5, 0.5))
        
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(color)
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.8)
        
        # Add extra shine for paved surfaces
        if tags.get('surface') == 'paving_stones':
            shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.1)
            shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.7)
        
        UsdShade.MaterialBindingAPI(road).Bind(material)

    def create_building(self, stage, way_id, coords, tags):
        """Create a building mesh using transformed coordinates."""
        building_path = f'/World/Buildings/building_{way_id}'
        building = UsdGeom.Mesh.Define(stage, building_path)
        
        # Get building height
        height = self.get_height(tags)
        
        # Create vertices with transformed coordinates
        points = []
        for x, z in coords:
            points.extend([
                Gf.Vec3f(x, 0, z),                        # bottom vertex
                Gf.Vec3f(x, height * self.HEIGHT_SCALE, z)  # top vertex
            ])
        
        # Create face indices
        num_vertices = len(coords)
        face_indices = []
        vertex_counts = []
        
        # Bottom face
        bottom_face = list(range(0, num_vertices * 2, 2))
        face_indices.extend(bottom_face)
        vertex_counts.append(len(bottom_face))
        
        # Top face
        top_face = list(range(1, num_vertices * 2, 2))
        face_indices.extend(top_face)
        vertex_counts.append(len(top_face))
        
        # Side faces
        for i in range(num_vertices):
            next_i = (i + 1) % num_vertices
            face_indices.extend([
                i * 2, i * 2 + 1, next_i * 2 + 1, next_i * 2
            ])
            vertex_counts.append(4)
        
        # Set mesh attributes
        building.CreatePointsAttr(points)
        building.CreateFaceVertexIndicesAttr(face_indices)
        building.CreateFaceVertexCountsAttr(vertex_counts)
        
        # Add metadata from tags using proper USD API
        primvars_api = UsdGeom.PrimvarsAPI(building)
        for key, value in tags.items():
            safe_key = key.replace(":", "_")  # Replace invalid characters
            primvar = primvars_api.CreatePrimvar(f'customData_{safe_key}', 
                                               Sdf.ValueTypeNames.String)
            primvar.Set(str(value))
        
        # Create a simple material
        material = UsdShade.Material.Define(stage, f'{building_path}/material')
        shader = UsdShade.Shader.Define(stage, f'{building_path}/material/PBRShader')
        shader.CreateIdAttr('UsdPreviewSurface')
        
        # Set material properties
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.4)
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.0)
        
        # Bind material to mesh
        UsdShade.MaterialBindingAPI(building).Bind(material)

    def export_to_usd(self, output_path: str):
        """Export the data to USD format."""
        stage = Usd.Stage.CreateNew(output_path)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        
        # Calculate center from all collected coordinates
        if not self.all_coords:
            print("No coordinates found")
            return
        
        center_lon = sum(c[0] for c in self.all_coords) / len(self.all_coords)
        center_lat = sum(c[1] for c in self.all_coords) / len(self.all_coords)
        
        print(f"Center coordinates: {center_lon}, {center_lat}")
        print(f"Total coordinates: {len(self.all_coords)}")
        print(f"Total buildings: {len(self.ways)}")
        
        # Create scopes for organization
        root = UsdGeom.Xform.Define(stage, '/World')
        buildings = UsdGeom.Scope.Define(stage, '/World/Buildings')
        water = UsdGeom.Scope.Define(stage, '/World/Water')
        land = UsdGeom.Scope.Define(stage, '/World/Land')
        roads = UsdGeom.Scope.Define(stage, '/World/Roads')
        
        # Create ground plane with map texture
        self.create_ground_plane(stage, center_lon, center_lat)
        
        # Create buildings
        print("Creating buildings...")
        for way_id, tags, nodes in self.ways:
            coords = []
            for node_id in nodes:
                if node_id in self.nodes:
                    coords.append(self.nodes[node_id])
            
            if coords:
                transformed_coords = self.transform_coordinates(coords, center_lon, center_lat)
                self.create_building(stage, way_id, transformed_coords, tags)
        
        # Create water features
        for coords, tags in self.water_features:
            transformed_coords = self.transform_coordinates(coords, center_lon, center_lat)
            self.create_water_feature(stage, transformed_coords, tags)
        
        # Create land features
        for coords, tags in self.land_features:
            transformed_coords = self.transform_coordinates(coords, center_lon, center_lat)
            self.create_land_feature(stage, transformed_coords, tags)
        
        # Create roads
        for coords, tags, width in self.roads:
            transformed_coords = self.transform_coordinates(coords, center_lon, center_lat)
            self.create_road(stage, transformed_coords, width, tags)
        
        stage.Save()
        print(f"USD file saved to: {output_path}")

    def process_osm_file(self, osm_path: str):
        """Process OSM file using osmium."""
        try:
            handler = OsmHandler(self)
            handler.apply_file(osm_path, locations=True)  # Enable locations
        except Exception as e:
            print(f"Error processing OSM file: {e}")

    def fetch_tiles(self, min_lat, max_lat, min_lon, max_lon, zoom=17):
        """Fetch all tiles for the given coordinate range"""
        # Calculate tile coordinates for bounds
        min_xtile, max_ytile = deg2num(min_lat, min_lon, zoom)
        max_xtile, min_ytile = deg2num(max_lat, max_lon, zoom)
        
        print(f"Tile coordinates: X({min_xtile}-{max_xtile}), Y({min_ytile}-{max_ytile})")
        
        # Calculate image dimensions
        tile_size = 256
        width = (max_xtile - min_xtile + 1) * tile_size
        height = (max_ytile - min_ytile + 1) * tile_size
        
        # Create new image
        result = Image.new('RGB', (width, height))
        
        # Download and stitch tiles
        for xtile in range(min_xtile, max_xtile + 1):
            for ytile in range(min_ytile, max_ytile + 1):
                url = f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"
                headers = {'User-Agent': 'OSM-to-USD-Converter/1.0'}
                
                try:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        tile = Image.open(BytesIO(response.content))
                        x = (xtile - min_xtile) * tile_size
                        y = (ytile - min_ytile) * tile_size
                        result.paste(tile, (x, y))
                        print(f"Downloaded tile {xtile},{ytile}")
                    else:
                        print(f"Failed to download tile {xtile},{ytile}: {response.status_code}")
                except Exception as e:
                    print(f"Error downloading tile {xtile},{ytile}: {e}")
                    return None
        
        return result

class OsmHandler(osmium.SimpleHandler):
    def __init__(self, json_handler):
        super(OsmHandler, self).__init__()
        self.json_handler = json_handler
        self.wkb_factory = osmium.geom.WKBFactory()
    
    def node(self, n):
        """Store node coordinates."""
        try:
            self.json_handler.nodes[n.id] = (n.location.lon, n.location.lat)
        except Exception as e:
            print(f"Error processing node {n.id}: {e}")
    
    def way(self, w):
        """Process way elements."""
        try:
            # Skip ways without tags
            if not w.tags:
                return
            
            # Extract nodes using stored coordinates
            nodes = []
            node_refs = []
            for node in w.nodes:
                if node.ref in self.json_handler.nodes:
                    nodes.append(self.json_handler.nodes[node.ref])
                    node_refs.append(node.ref)
            
            if not nodes:
                return
                
            tags = {tag.k: tag.v for tag in w.tags}
            
            # Check if way crosses our area of interest
            lons, lats = zip(*nodes)
            if not (min(lons) <= self.json_handler.max_lon and 
                    max(lons) >= self.json_handler.min_lon and
                    min(lats) <= self.json_handler.max_lat and 
                    max(lats) >= self.json_handler.min_lat):
                return  # Skip if not in our area
            
            # Process different types of ways
            if 'building' in tags:
                self.json_handler.process_way({
                    'id': w.id,
                    'nodes': node_refs,
                    'tags': tags
                })
            elif 'highway' in tags or 'amenity' in tags:  # Added amenity check
                self.json_handler.process_road({
                    'nodes': nodes,
                    'tags': tags,
                    'id': w.id
                })
            elif any(k in tags for k in ['water', 'waterway', 'natural', 'landuse', 'leisure']):
                self.json_handler.classify_feature({
                    'nodes': node_refs,  # Changed from nodes to node_refs
                    'tags': tags,
                    'id': w.id
                })
                
        except Exception as e:
            print(f"Error processing way {w.id}: {e}")

def main():
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    json_path = os.path.join(current_dir, 'samples', 'export.json')
    osm_path = os.path.join(current_dir, 'samples', 'map.osm')
    usd_path = os.path.join(current_dir, 'output', 'osm_buildings.usda')
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(usd_path), exist_ok=True)
    
    try:
        # Create handler
        handler = JsonHandler()
        
        # Process OSM file first (for base features)
        if os.path.exists(osm_path):
            print(f"Processing OSM file: {osm_path}")
            handler.process_osm_file(osm_path)
            print(f"Found {len(handler.nodes)} nodes")
            print(f"Found {len(handler.ways)} ways")
            print(f"Found {len(handler.water_features)} water features")
            print(f"Found {len(handler.land_features)} land features")
        
        # Process JSON file (for additional features)
        if os.path.exists(json_path):
            print(f"Processing JSON file: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                handler.process_json(json_data)
        
        # Export to USD
        print(f"Exporting to USD: {usd_path}")
        handler.export_to_usd(usd_path)
        print("Export complete!")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 