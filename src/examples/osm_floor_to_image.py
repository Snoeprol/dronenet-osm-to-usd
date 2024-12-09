import os
import requests
import math
from PIL import Image
from io import BytesIO
from pxr import Usd, UsdGeom, Sdf, UsdShade, Gf

def deg2num(lat_deg, lon_deg, zoom):
    """Convert latitude/longitude to tile coordinates"""
    lat_rad = math.radians(lat_deg)
    n = 1 << zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def get_osm_image(min_lat, max_lat, min_lon, max_lon, zoom=17):
    """Download and stitch OSM tiles for the given area"""
    # Calculate tile coordinates
    min_xtile, max_ytile = deg2num(min_lat, min_lon, zoom)
    max_xtile, min_ytile = deg2num(max_lat, max_lon, zoom)
    
    # Ensure we don't download too many tiles
    if (max_xtile - min_xtile + 1) * (max_ytile - min_ytile + 1) > 25:
        print("Warning: Large area might require too many tiles. Consider reducing zoom level.")
        return None
    
    # Calculate total image size
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
                tile = Image.open(BytesIO(response.content))
                
                # Calculate position in final image
                x = (xtile - min_xtile) * tile_size
                y = (ytile - min_ytile) * tile_size
                result.paste(tile, (x, y))
                
            except Exception as e:
                print(f"Error downloading tile {xtile},{ytile}: {e}")
                return None
    
    return result

def create_textured_ground(stage, image_path, center_lon, center_lat, scale=2000):
    """Create a textured ground plane in USD aligned with the center coordinates"""
    ground = UsdGeom.Mesh.Define(stage, '/World/Ground')
    
    # Create a large ground plane centered at the calculated center
    size = scale * 1.5
    points = [
        Gf.Vec3f(-size, -0.1, -size),  # Bottom-left
        Gf.Vec3f(size, -0.1, -size),   # Bottom-right
        Gf.Vec3f(size, -0.1, size),    # Top-right
        Gf.Vec3f(-size, -0.1, size),   # Top-left
    ]
    
    # Define UV coordinates (flipped vertically to match OSM orientation)
    texCoords = [(0, 1), (1, 1), (1, 0), (0, 0)]
    
    face_indices = [0, 1, 2, 3]
    vertex_counts = [4]
    
    # Set mesh attributes
    ground.CreatePointsAttr(points)
    ground.CreateFaceVertexIndicesAttr(face_indices)
    ground.CreateFaceVertexCountsAttr(vertex_counts)
    
    # Create UV coordinates primvar
    texCoordPrimvar = UsdGeom.PrimvarsAPI(ground).CreatePrimvar(
        'st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    texCoordPrimvar.Set(texCoords)
    
    # Create material and shader
    material = UsdShade.Material.Define(stage, '/World/Ground/material')
    shader = UsdShade.Shader.Define(stage, '/World/Ground/material/PBRShader')
    shader.CreateIdAttr('UsdPreviewSurface')
    
    # Create texture shader
    stReader = UsdShade.Shader.Define(stage, '/World/Ground/material/stReader')
    stReader.CreateIdAttr('UsdPrimvarReader_float2')
    stReader.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('st')
    
    # Create texture sampler
    diffuseTextureSampler = UsdShade.Shader.Define(
        stage, '/World/Ground/material/diffuseTexture')
    diffuseTextureSampler.CreateIdAttr('UsdUVTexture')
    diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(image_path)
    diffuseTextureSampler.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(
        stReader.ConnectableAPI(), 'result')
    
    # Connect texture to shader
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(
        diffuseTextureSampler.ConnectableAPI(), 'rgb')
    
    # Add slight transparency to blend with other features
    shader.CreateInput('opacity', Sdf.ValueTypeNames.Float).Set(0.95)
    
    # Bind material
    UsdShade.MaterialBindingAPI(ground).Bind(material)

def main():
    # Den Helder coordinates (matching parse_json.py)
    min_lat = 52.96
    max_lat = 52.96 + 0.005  # Matching the exact range from parse_json.py
    min_lon = 4.78575
    max_lon = 4.78775
    
    # Calculate center coordinates (matching parse_json.py's center calculation)
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    
    print(f"Center coordinates: {center_lon}, {center_lat}")
    
    # Create output directories
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_dir = os.path.join(current_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Download OSM image
    print("Downloading OSM tiles...")
    image = get_osm_image(min_lat, max_lat, min_lon, max_lon)
    
    if image:
        # Save the image
        image_path = os.path.join(output_dir, 'den_helder_map.png')
        image.save(image_path)
        print(f"Map image saved to: {image_path}")
        
        # Create USD stage with textured ground
        usd_path = os.path.join(output_dir, 'den_helder_ground.usda')
        stage = Usd.Stage.CreateNew(usd_path)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        
        # Add textured ground with center coordinates
        create_textured_ground(stage, image_path, center_lon, center_lat, scale=2000)  # Matching SCALE from parse_json.py
        
        # Save USD file
        stage.Save()
        print(f"USD file saved to: {usd_path}")
    else:
        print("Failed to download map image")

if __name__ == "__main__":
    main()
