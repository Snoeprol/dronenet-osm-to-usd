import requests
from PIL import Image
from io import BytesIO
import math
from pxr import Usd, UsdGeom, Sdf, UsdShade, Gf
import os

def deg2num(lat_deg, lon_deg, zoom):
    """Convert latitude/longitude to tile coordinates"""
    lat_rad = math.radians(lat_deg)
    n = 1 << zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def create_background(stage, image_path):
    """Create a background in USD following official USD guidelines"""
    # Create a camera that looks at our background
    camera = UsdGeom.Camera.Define(stage, '/World/Camera')
    camera.CreateProjectionAttr('orthographic')
    camera.CreateHorizontalApertureAttr(20.955)
    camera.CreateVerticalApertureAttr(20.955)
    
    # Create background plane
    background = UsdGeom.Mesh.Define(stage, '/World/Background')
    
    # Set purpose to 'background' as per USD guidelines
    background.CreatePurposeAttr('background')
    
    # Create a plane that fills the camera view
    points = [
        Gf.Vec3f(-10, -10, -1),  # Bottom-left
        Gf.Vec3f(10, -10, -1),   # Bottom-right
        Gf.Vec3f(10, 10, -1),    # Top-right
        Gf.Vec3f(-10, 10, -1),   # Top-left
    ]
    
    # UV coordinates for proper texture mapping
    texCoords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    
    face_indices = [0, 1, 2, 3]
    vertex_counts = [4]
    
    background.CreatePointsAttr(points)
    background.CreateFaceVertexIndicesAttr(face_indices)
    background.CreateFaceVertexCountsAttr(vertex_counts)
    
    # Create UV coordinates primvar
    texCoordPrimvar = UsdGeom.PrimvarsAPI(background).CreatePrimvar(
        'st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    texCoordPrimvar.Set(texCoords)
    
    # Create material following USD Preview Surface spec
    material = UsdShade.Material.Define(stage, '/World/Background/material')
    pbrShader = UsdShade.Shader.Define(stage, '/World/Background/material/PBRShader')
    pbrShader.CreateIdAttr('UsdPreviewSurface')
    
    # Create texture reader
    stReader = UsdShade.Shader.Define(stage, '/World/Background/material/stReader')
    stReader.CreateIdAttr('UsdPrimvarReader_float2')
    stReader.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('st')
    
    # Create texture sampler
    textureSampler = UsdShade.Shader.Define(stage, '/World/Background/material/diffuseTexture')
    textureSampler.CreateIdAttr('UsdUVTexture')
    textureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(image_path)
    textureSampler.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(
        stReader.ConnectableAPI(), 'result')
    
    # Make it emissive to ensure visibility
    pbrShader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(
        textureSampler.ConnectableAPI(), 'rgb')
    
    # Bind material
    UsdShade.MaterialBindingAPI(background).Bind(material)

def main():
    # Den Helder coordinates
    lat = 52.95784
    lon = 4.79160
    zoom = 17
    
    # Get tile coordinates
    xtile, ytile = deg2num(lat, lon, zoom)
    
    # Download the tile
    url = f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"
    headers = {'User-Agent': 'Simple-OSM-USD-Example/1.0'}
    
    print(f"Downloading tile for coordinates: {lat}, {lon}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Save the tile
        tile = Image.open(BytesIO(response.content))
        image_path = "output/background_tile.png"
        os.makedirs("output", exist_ok=True)
        tile.save(image_path)
        
        # Create USD stage
        stage = Usd.Stage.CreateNew("output/background.usda")
        
        # Set up stage
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        
        # Create background with the image
        create_background(stage, image_path)
        
        # Save USD file
        stage.Save()
        print("Created USD background!")

if __name__ == "__main__":
    main()
