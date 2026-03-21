import os
from supabase import create_client, Client

class StorageService:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            print("Warning: Supabase credentials not found.")
            self.supabase: Client = None
        else:
            self.supabase: Client = create_client(url, key)
            self.bucket_name = "certificados"

    def upload_file(self, file_bytes: bytes, path: str, content_type: str = "application/pdf"):
        """Sube un archivo a Supabase Storage. Retorna (resultado, error_msg)"""
        if not self.supabase:
            return None, "Supabase client not initialized"
            
        try:
            res = self.supabase.storage.from_(self.bucket_name).upload(
                file=file_bytes,
                path=path,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            return res, None
        except Exception as e:
            import traceback
            err_msg = str(e)
            print(f"Error uploading to Supabase: {err_msg}")
            traceback.print_exc()
            return None, err_msg

    def get_public_url(self, path: str):
        """Obtiene la URL pública del archivo."""
        if not self.supabase:
            return None
            
        try:
            # get_public_url in some versions returns a string, in others an object
            res = self.supabase.storage.from_(self.bucket_name).get_public_url(path)
            if hasattr(res, 'public_url'):
                return str(res.public_url)
            return str(res)
        except Exception as e:
            print(f"Error getting public URL: {e}")
            return None

storage_service = StorageService()
