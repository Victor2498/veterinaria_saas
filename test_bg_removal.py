import sys
import os
import io
from PIL import Image

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.services.image_processor import process_transparency, create_mock_signature

def test_transparency():
    print("Testing Background Removal...")
    
    # 1. Create a mock signature with a white background (JPEG)
    mock_sig_bytes = create_mock_signature("Dr. Test Signature")
    
    with open("test_input_white.jpg", "wb") as f:
        f.write(mock_sig_bytes)
    print("✅ Created test_input_white.jpg")
    
    # 2. Process it
    transparent_bytes = process_transparency(mock_sig_bytes)
    
    with open("test_output_transparent.png", "wb") as f:
        f.write(transparent_bytes)
    print("✅ Created test_output_transparent.png")
    
    # 3. Verify transparency with PIL
    img = Image.open(io.BytesIO(transparent_bytes))
    if img.mode == 'RGBA':
        print("✅ Output is RGBA")
        # Check a pixel that should be transparent (corner)
        pixel = img.getpixel((0, 0))
        if pixel[3] == 0:
            print("✅ Corner pixel is transparent!")
        else:
            print(f"❌ Corner pixel alpha is {pixel[3]}, expected 0")
    else:
        print(f"❌ Output mode is {img.mode}, expected RGBA")

if __name__ == "__main__":
    test_transparency()
    print("\nNext: Run test_pro_certificate.py to see it in the PDF context.")
