import io
from PIL import Image, ImageChops

def process_transparency(image_bytes: bytes, threshold: int = 220) -> bytes:
    """
    Toma una imagen (bytes), quita el fondo blanco/claro y la devuelve como PNG transparente.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        datas = img.getdata()
        
        new_data = []
        for item in datas:
            # item is (R, G, B, A)
            # Si el promedio de los colores es mayor al threshold, asumimos que es fondo
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                new_data.append((255, 255, 255, 0)) # Transparente
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        
        # Opcional: Recortar bordes vacíos (autocrop)
        # alpha = img.getchannel('A')
        # bbox = alpha.getbbox()
        # if bbox:
        #     img = img.crop(bbox)

        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"❌ Error procesando transparencia: {e}")
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
