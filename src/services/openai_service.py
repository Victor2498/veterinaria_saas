import os
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_chat_completion(messages, api_key=None, model="gpt-4o", temperature=0.7):
    # Dynamic client if api_key is provided
    local_client = AsyncOpenAI(api_key=api_key) if api_key else client
    try:
        response = await local_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return "Lo siento, tengo un problema técnico. ¿Podrías repetir o llamar a la clínica? 🐾"

async def get_vision_completion(prompt, base64_image, api_key=None, model="gpt-4o"):
    """Analiza una imagen usando GPT-4o y devuelve una descripción/análisis."""
    local_client = AsyncOpenAI(api_key=api_key) if api_key else client
    try:
        response = await local_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ],
                }
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI Vision Error: {e}")
        return "No pude analizar la imagen correctamente. ¿Podrías describirme lo que ves? 🐾"

async def transcribe_audio_file(file_path, api_key=None):
    local_client = AsyncOpenAI(api_key=api_key) if api_key else client
    try:
        with open(file_path, "rb") as audio_file:
            transcription = await local_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )
        return transcription.text
    except Exception as e:
        print(f"❌ OpenAI Transcription Error: {e}")
        return ""
