from pxr import Usd, UsdGeom, Gf

def create_simple_cube():
    # Create a new stage
    stage = Usd.Stage.CreateNew("output/simple_cube.usda")
    
    # Set up meters as our working unit
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    
    # Create a cube
    cube = UsdGeom.Cube.Define(stage, '/World/Cube')
    
    # Set the cube's size (default is 2 units, let's make it 1 meter)
    cube.CreateSizeAttr(1.0)
    
    # Position the cube slightly above ground
    cube.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.5))
    
    # Save the stage
    stage.Save()
    print("Created simple_cube.usda")

if __name__ == "__main__":
    create_simple_cube()