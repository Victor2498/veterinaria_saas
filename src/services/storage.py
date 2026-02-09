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
            self.bucket_name = "certificados-premium"

    def upload_file(self, file_bytes: bytes, path: str, content_type: str = "application/pdf"):
        """Sube un archivo a Supabase Storage."""
        if not self.supabase:
            return None
            
        try:
            # Check if bucket exists, create if not (optional, usually manual setup)
            # For now assume bucket exists
            
            res = self.supabase.storage.from_(self.bucket_name).upload(
                file=file_bytes,
                path=path,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            return res
        except Exception as e:
            print(f"Error uploading to Supabase: {e}")
            return None

    def get_public_url(self, path: str):
        """Obtiene la URL pública del archivo."""
        if not self.supabase:
            return None
            
        try:
            res = self.supabase.storage.from_(self.bucket_name).get_public_url(path)
            return res
        except Exception as e:
            print(f"Error getting public URL: {e}")
            return None

storage_service = StorageService()
