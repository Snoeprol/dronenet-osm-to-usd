from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf
import os

def create_den_helder_cube():
    # Create the stage
    stage = Usd.Stage.CreateNew("output/den_helder_cube.usda")
    
    # Create a cube
    cube = UsdGeom.Cube.Define(stage, "/World/Cube")
    
    # Add texture coordinates (UV) through primvars
    texCoords = UsdGeom.PrimvarsAPI(cube).CreatePrimvar(
        "st",  # UV coordinates are typically called "st" in USD
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying  # Use faceVarying for per-face texturing
    )
    
    # Set UV coordinates for the cube - one set per face vertex
    texCoords.Set([
        # Front face
        (0, 0), (1, 0), (1, 1), (0, 1),
        # Back face
        (0, 0), (1, 0), (1, 1), (0, 1),
        # Top face
        (0, 0), (1, 0), (1, 1), (0, 1),
        # Bottom face
        (0, 0), (1, 0), (1, 1), (0, 1),
        # Right face
        (0, 0), (1, 0), (1, 1), (0, 1),
        # Left face
        (0, 0), (1, 0), (1, 1), (0, 1),
    ])
    
    # Set indices for the UV coordinates
    texCoords.SetIndices([
        # Front face
        0, 1, 2, 3,
        # Back face
        4, 5, 6, 7,
        # Top face
        8, 9, 10, 11,
        # Bottom face
        12, 13, 14, 15,
        # Right face
        16, 17, 18, 19,
        # Left face
        20, 21, 22, 23
    ])
    
    # Create material
    material = UsdShade.Material.Define(stage, "/World/Cube/Material")
    
    # Create PBR shader
    pbrShader = UsdShade.Shader.Define(stage, "/World/Cube/Material/PBRShader")
    pbrShader.CreateIdAttr("UsdPreviewSurface")
    
    # Create primvar reader for UV coordinates
    stReader = UsdShade.Shader.Define(stage, "/World/Cube/Material/stReader")
    stReader.CreateIdAttr("UsdPrimvarReader_float2")
    stReader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    
    # Create texture sampler
    diffuseTexture = UsdShade.Shader.Define(stage, "/World/Cube/Material/diffuseTexture")
    diffuseTexture.CreateIdAttr("UsdUVTexture")
    
    # Set texture wrapping mode to repeat
    diffuseTexture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
    diffuseTexture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
    
    # Get the absolute path to the ground texture
    current_dir = os.path.dirname(os.path.abspath(__file__))
    texture_path = os.path.join(current_dir, "../../output/ground_texture.png")
    
    # Set the texture file path
    diffuseTexture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)
    
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
    
    # Bind material to cube
    UsdShade.MaterialBindingAPI(cube).Bind(material)
    
    # Save the stage
    stage.Save()

if __name__ == "__main__":
    create_den_helder_cube() 