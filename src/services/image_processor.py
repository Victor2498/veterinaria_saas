import io
from PIL import Image, ImageChops

def process_transparency(image_bytes: bytes, threshold: int = 220, intensity_gain: float = 1.5) -> bytes:
    """
    Mejora avanzada: convierte el brillo en transparencia inversa.
    Cualquier color muy claro se vuelve transparente, y los oscuros se mantienen sólidos.
    intensity_gain: ayuda a que la tinta se vea más fuerte/negra.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        # Convertir a escala de grises para calcular intensidad
        grayscale = img.convert("L")
        
        datas = img.getdata()
        gray_datas = grayscale.getdata()
        
        new_data = []
        for i in range(len(datas)):
            r, g, b, a = datas[i]
            luma = gray_datas[i]
            
            # Mapeo de transparencia:
            # Si luma > 250 -> alpha 0
            # Si luma < 180 -> alpha 255
            # Interpolación lineal en el medio
            if luma > 250:
                alpha = 0
            elif luma < 180:
                alpha = 255
            else:
                alpha = int((250 - luma) / (250 - 180) * 255)
            
            # Oscurecer la tinta (contraste): 
            # Multiplicamos los canales originales para que la tinta sea más sólida
            # Si es firma azul, queremos que siga siendo azul pero fuerte.
            if alpha > 0:
                f = 1.0 / intensity_gain
                r = int(max(0, r * f))
                g = int(max(0, g * f))
                b = int(max(0, b * f))
            
            new_data.append((r, g, b, alpha))
        
        img.putdata(new_data)
        
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
