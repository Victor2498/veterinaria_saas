import io
from PIL import Image

def process_transparency(image_bytes: bytes, threshold: int = 220, intensity_gain: float = 1.5) -> bytes:
    """
    Mejora avanzada: convierte el brillo en transparencia inversa.
    Cualquier color muy claro se vuelve transparente, y los oscuros se mantienen sólidos.
    intensity_gain: ayuda a que la tinta se vea más fuerte/negra.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        # Convert to grayscale to calculate intensity
        grayscale = img.convert("L")
        
        # Lookup Table (LUT) for transparency mapping
        lut_alpha = []
        for luma in range(256):
            if luma > 245:
                alpha = 0
            elif luma < 160:
                alpha = 255
            else:
                alpha = int((245 - luma) / (245 - 160) * 255)
            lut_alpha.append(alpha)
        
        # LUT for color enhancement (darkening)
        f = 1.0 / intensity_gain
        lut_color = [int(max(0.0, float(i) * f)) for i in range(256)]
        
        # Apply LUTs
        alpha_channel = grayscale.point(lut_alpha)
        
        # Split channels and apply enhancement to RGB
        r, g, b, _ = img.split()
        r = r.point(lut_color)
        g = g.point(lut_color)
        b = b.point(lut_color)
        
        # Merge back with the new alpha
        img = Image.merge("RGBA", (r, g, b, alpha_channel))
        
        # Recortar bordes vacíos automáticamente (Autocrop)
        bbox = img.getchannel('A').getbbox()
        if bbox:
            img = img.crop(bbox)

        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"❌ Error avanzado de transparencia: {e}")
        return image_bytes

def process_firma_sello(image_bytes: bytes) -> bytes:
    """
    Pipeline completo: 
    1. Redimensiona si > 2000px
    2. Quita fondo blanco (> 240) y convierte a transparencia gradualmente
    3. Autorecortar bordes vacíos
    4. Guardar como PNG optimizado.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        # 1. Normalización: redimensionar si supera los 2000px
        max_dim = 2000
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
        # 2. Eliminación de fondo blanco via LUT (Mucho más rápido que loops)
        grayscale = img.convert("L")
        
        lut_alpha = []
        for luma in range(256):
            if luma > 240:
                alpha = 0
            elif luma < 160:
                alpha = 255
            else:
                alpha = int((240 - luma) / (240 - 160) * 255)
            lut_alpha.append(alpha)
            
        alpha_channel = grayscale.point(lut_alpha)
        img.putalpha(alpha_channel)
        
        # 3. Autocrop
        bbox = img.getchannel('A').getbbox()
        if bbox:
            img = img.crop(bbox)
            
        # 4. Optimizar PNG
        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)
        return output.getvalue()
    except Exception as e:
        print(f"❌ Error processing background removal: {e}")
        raise e

def create_mock_signature(text="Firma"):
    """Crea una firma de prueba (texto negro sobre fondo blanco) para verificar el procesador."""
    from PIL import ImageDraw, ImageFont
    img = Image.new('RGB', (200, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        # Intentar cargar una fuente por defecto de Windows
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    d.text((10, 30), text, fill=(0, 0, 50), font=font) # Azul oscuro
    
    output = io.BytesIO()
    img.save(output, format="JPEG")
    return output.getvalue()
