from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf
import os

def create_den_helder_surface():
    # Create the stage
    stage = Usd.Stage.CreateNew("output/den_helder_surface.usda")
    
    # Create a mesh for the surface
    surface = UsdGeom.Mesh.Define(stage, "/World/Surface")
    
    # Define the vertices for a flat rectangular surface
    points = [
        Gf.Vec3f(-5, 0, -5),  # Bottom-left
        Gf.Vec3f(5, 0, -5),   # Bottom-right
        Gf.Vec3f(5, 0, 5),    # Top-right
        Gf.Vec3f(-5, 0, 5),   # Top-left
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
    
    # Set UV coordinates for the surface
    texCoords.Set([
        (0, 0),  # Bottom-left
        (1, 0),  # Bottom-right
        (1, 1),  # Top-right
        (0, 1),  # Top-left
    ])
    
    # Create material
    material = UsdShade.Material.Define(stage, "/World/Surface/Material")
    
    # Create PBR shader
    pbrShader = UsdShade.Shader.Define(stage, "/World/Surface/Material/PBRShader")
    pbrShader.CreateIdAttr("UsdPreviewSurface")
    
    # Create primvar reader for UV coordinates
    stReader = UsdShade.Shader.Define(stage, "/World/Surface/Material/stReader")
    stReader.CreateIdAttr("UsdPrimvarReader_float2")
    stReader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    
    # Create texture sampler
    diffuseTexture = UsdShade.Shader.Define(stage, "/World/Surface/Material/diffuseTexture")
    diffuseTexture.CreateIdAttr("UsdUVTexture")
    
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
    
    # Bind material to surface
    UsdShade.MaterialBindingAPI(surface).Bind(material)
    
    # Save the stage
    stage.Save()

if __name__ == "__main__":
    create_den_helder_surface()
