import os
import aiohttp
import base64
import tempfile
from datetime import datetime

async def extract_audio_bytes(data: dict, audio_msg: dict) -> bytes | None:
    """
    Extrae los bytes del audio desde el webhook de Evolution API.
    Soporta descarga por URL y extracción directa de Base64.
    """
    # 1. Intentar obtener Base64 directo (si está disponible)
    audio_base64 = audio_msg.get("base64") or data.get("base64")
    if audio_base64:
        try:
            return base64.b64decode(audio_base64)
        except Exception:
            pass

    # 2. Intentar descargar desde URL
    url = audio_msg.get("url") or data.get("mediaUrl")
    if url:
        # En Evolution API, a veces necesitamos el apikey para descargar la media
        api_key = os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN")
        headers = {"apikey": api_key} if api_key else {}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        print(f"❌ Error descargando audio: {resp.status}")
            except Exception as e:
                print(f"❌ Error en petición de audio: {e}")

    return None

async def save_temp_audio(audio_bytes: bytes, filename: str) -> str:
    """
    Guarda los bytes en un archivo temporal y devuelve la ruta absoluta.
    Utiliza una subcarpeta 'temp_audio' para organización.
    """
    base_dir = "temp_audio"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        
    file_path = os.path.join(base_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
        
    return os.path.abspath(file_path)

def is_valid_audio_header(data: bytes) -> bool:
    """Valida los Magic Bytes del audio."""
    if not data or len(data) < 12: return False
    
    # OGG/Opus (WhatsApp nativo), RIFF (WAV), ID3 (MP3)
    if data.startswith(b'OggS') or data.startswith(b'RIFF') or data.startswith(b'ID3') or data.startswith(b'\xFF\xFB'):
        return True
        
    return False
