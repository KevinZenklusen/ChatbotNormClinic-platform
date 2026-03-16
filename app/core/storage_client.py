from abc import ABC, abstractmethod
from app.core.config import STORAGE_MODE, LOCAL_STORAGE_PATH, SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET
from supabase import create_client
import os
import uuid
from pathlib import Path

class FileStorageClient(ABC):

    @abstractmethod
    def save(self, file_path: str, content: bytes):
        pass


class LocalStorageClient(FileStorageClient):

    def __init__(self, base_path):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save(self, file_path, content):
        full_path = os.path.join(self.base_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        return full_path


class SupabaseStorageClient(FileStorageClient):

    def __init__(self, url, key, bucket):
        self.client = create_client(url, key)
        self.bucket = bucket

    def save(self, file_path, content):
        self.client.storage.from_(self.bucket).upload(
            file_path,
            content,
            {"content-type": "application/pdf"}
        )
        return file_path
    

def get_storage_client():
    print(f"Storage: {STORAGE_MODE}")
    if STORAGE_MODE == "local":
        print("Storage local")
        return LocalStorageClient(LOCAL_STORAGE_PATH)
    elif STORAGE_MODE == "online":
        print("Storage Supabase")
        return SupabaseStorageClient(
            SUPABASE_URL,
            SUPABASE_KEY,
            SUPABASE_BUCKET
        )
    else:
        print("Storage Mode not defined")
    
def save_file_in_blob_storage(
    *,
    file_bytes: bytes,
    filename: str,
    user_uid: str
) -> str:
    storage = get_storage_client()

    file_id = str(uuid.uuid4())
    safe_name = filename.replace(" ", "_")

    relative_path = f"{user_uid}/{file_id}_{safe_name}"

    stored_path = storage.save(relative_path, file_bytes)

    if STORAGE_MODE == "local":
        full_path = Path(stored_path).resolve()
        return f"file://{full_path}"
    elif STORAGE_MODE == "online":
        # Supabase
        return f"supabase://{SUPABASE_BUCKET}/{stored_path}"
    else:
        print("Storage Mode not defined") 
    
