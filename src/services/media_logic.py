import os
import aiohttp
import base64

def is_valid_media(data: bytes, media_type: str) -> bool:
    """Valida si los bytes corresponden al tipo de media esperado."""
    if not data or len(data) < 12: return False
    
    if media_type == "audio":
        # Magic Bytes for Audio
        if data.startswith(b'OggS'): return True # OGG
        if data.startswith(b'RIFF'): return True # WAV
        if data.startswith(b'ID3') or data.startswith(b'\xFF\xFB'): return True # MP3
    elif media_type == "image":
        # Magic Bytes for Images
        if data.startswith(b'\xFF\xD8\xFF'): return True # JPEG
        if data.startswith(b'\x89PNG\r\n\x1a\n'): return True # PNG
        if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'): return True # GIF
        if data.startswith(b'RIFF') and data[8:12] == b'WEBP': return True # WEBP
        
    return False

async def extract_media_base64(data: dict, message_obj: dict, media_key: str, api_key: str = None) -> str | None:
    """
    Extrae el contenido de media y lo devuelve como string Base64 para OpenAI.
    """
    key = api_key or os.getenv("EVOLUTION_API_KEY")
    
    # Intentar obtener base64 directo
    media_base64 = (
        message_obj.get("base64") or 
        data.get("base64") or 
        data.get("message", {}).get("base64")
    )
    
    if media_base64:
        return media_base64

    # Intentar descargar desde URL si no hay base64
    url = message_obj.get("url") or data.get("mediaUrl") or message_obj.get("mediaUrl")
    if url:
        async with aiohttp.ClientSession() as session:
            try:
                headers = {"apikey": key}
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        return base64.b64encode(content).decode('utf-8')
            except Exception as e:
                print(f"❌ Error descargando media: {e}")

    return None
