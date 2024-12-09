from PIL import Image, ImageDraw
import os

def create_test_texture():
    # Create a 512x512 texture
    size = 512
    img = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw a more distinctive pattern
    # Border
    draw.rectangle([0, 0, size-1, size-1], outline='black', width=2)
    
    # Diagonal lines
    draw.line([(0, 0), (size, size)], fill='red', width=4)
    draw.line([(0, size), (size, 0)], fill='blue', width=4)
    
    # Center circle
    center = size // 2
    radius = size // 4
    draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                 outline='green', width=4)
    
    # Text to show orientation
    draw.text((10, 10), "TOP", fill='black', size=40)
    draw.text((10, size-50), "BOTTOM", fill='black', size=40)
    draw.text((size//2-20, size//2-10), "CENTER", fill='black', size=40)
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    # Save the texture
    img.save('output/texture.jpg')

if __name__ == "__main__":
    create_test_texture() 