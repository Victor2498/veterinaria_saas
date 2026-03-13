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

def extract_signature_only(image_bytes: bytes) -> bytes:
    """
    Intenta extraer solo la parte de la firma de una imagen compuesta (sello arriba, firma abajo).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        # Encontrar el area con contenido (non-transparent)
        alpha = img.getchannel('A')
        bbox = alpha.getbbox() # (left, top, right, bottom)
        
        if not bbox:
            return image_bytes
            
        # El sello suele estar arriba y la firma abajo.
        # Tomamos el 45% inferior del area de contenido.
        content_height = bbox[3] - bbox[1]
        signature_top = bbox[1] + int(content_height * 0.55)
        
        # Crop: (left, signature_top, right, bottom)
        signature_img = img.crop((bbox[0], signature_top, bbox[2], bbox[3]))
        
        # Autocrop final para quitar espacios vacios extra
        sig_alpha = signature_img.getchannel('A')
        sig_bbox = sig_alpha.getbbox()
        if sig_bbox:
            signature_img = signature_img.crop(sig_bbox)

        output = io.BytesIO()
        signature_img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        print(f"❌ Error extrayendo firma: {e}")
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
