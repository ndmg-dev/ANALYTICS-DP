import io
from minio import Minio
from minio.error import S3Error
import os
from urllib.parse import urlparse

class MinioClient:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "imports")
        
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error checking/creating bucket: {e}")

    def upload_file(self, file_stream: io.BytesIO, object_name: str, file_size: int, content_type: str = "application/vnd.ms-excel"):
        try:
            file_stream.seek(0)
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_stream,
                length=file_size,
                content_type=content_type
            )
            return True
        except S3Error as e:
            print(f"MinIO upload error: {e}")
            return False

    def get_file_stream(self, object_name: str) -> io.BytesIO:
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return io.BytesIO(response.read())
        except S3Error as e:
            print(f"MinIO download error: {e}")
            raise
        finally:
            if 'response' in locals():
                response.close()
