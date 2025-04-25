"""
This is a wrapper around aioboto3 to make it easier to upload and download files to R2.
"""
from aioboto3 import Session
from botocore.client import Config
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class R2Client:
    """Object storage client."""

    _instance = None

    def __new__(
        cls, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str="", region_name: str = "auto", config: Config = Config(signature_version="s3v4")
    ):
        if cls._instance is None:
            cls._instance = super(R2Client, cls).__new__(cls)
            cls._instance._initialize(endpoint_url, access_key_id, secret_access_key, bucket_name, region_name, config)
        return cls._instance

    def _initialize(
        self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str, region_name: str, config: Config
    ):
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.config = config
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize R2 client."""
        session = Session()
        return session.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=self.config,
            region_name=self.region_name,
        )

    def _select_bucket(self, bucket_name: str = ""):
        """Select the bucket to use."""
        if bucket_name:
            return bucket_name
        return self.bucket_name

    async def upload_file(self, key: str, filename: str, extra_args: Optional[Dict[Any, Any]] = None, bucket_name: str = ""):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_file(Filename=filename, Bucket=self._select_bucket(bucket_name), Key=key, ExtraArgs=extra_args or {})

    async def upload_fileobj(self, fileobj, key: str, extra_args: Optional[Dict[Any, Any]] = None, bucket_name: str = ""):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_fileobj(Fileobj=fileobj, Bucket=self._select_bucket(bucket_name), Key=key, ExtraArgs=extra_args or {})

    async def download_file(self, key: str, filename: str, bucket_name: str = ""):
        """Download file from R2."""
        async with self.client as client:
            await client.download_file(Bucket=self._select_bucket(bucket_name), Key=key, Filename=filename)

    async def upload_object(self, fileobj, key: str, bucket_name: str = "", metadata: Optional[Dict[Any, Any]] = None) -> bool:
        """Upload file to R2.
        
        Args:
            fileobj: The file object to upload
            key: The key to store the file under in R2
            bucket_name: Optional bucket name, defaults to instance bucket_name
            extra_args: Optional extra arguments for upload
            metadata: Optional metadata dictionary to attach to the object
        """
        ret = False
        async with self.client as client:
            try:
                response = await client.put_object(
                    Bucket=self._select_bucket(bucket_name), 
                    Key=key,
                    Body=fileobj,
                    Metadata=metadata or {}
                )
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    ret = True
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.error("Error uploading object: %s, key: %s", str(e), key)
        return ret

    async def download_object(self, key: str, bucket_name: str = "") -> Optional[bytes]:
        """Download file from R2.
        
        Args:
            key: The key of the file in R2
        
        Returns:
            bytes of the file content
        """
        async with self.client as client:
            try:
                response = await client.get_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return await response["Body"].read()
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.error("Error downloading file: %s, key: %s", str(e), key)
                return None
    
    async def check_object_exists(self, key: str, bucket_name: str = "") -> bool:
        """Check if an object exists in R2."""
        async with self.client as client:
            try:
                response = await client.head_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return response["ResponseMetadata"]["HTTPStatusCode"] == 200
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.warning("Error checking object exists: %s, key: %s", str(e), key)
                return False

    async def get_object_size(self, key: str, bucket_name: str = "") -> int:
        """Get the size of an object in R2."""
        try:
            async with self.client as client:
                response = await client.head_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return response["ContentLength"]
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error getting object size: %s, key: %s", str(e), key)
            return 0
        
    async def get_object_with_width_height(self, key: str, bucket_name: str = "") -> Tuple[float, float]:
        """Get the object with width and height."""
        try:
            async with self.client as client:
                response = await client.head_object(Bucket=self._select_bucket(bucket_name), Key=key)
                image_width = float(response.get("Metadata", {}).get("image_width", 0.0))
                image_height = float(response.get("Metadata", {}).get("image_height", 0.0))
                return image_width, image_height
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error getting object with width and height: %s, key: %s", str(e), key)
            return 0, 0

    async def generate_presigned_url(self, key: str, bucket_name: str = "", expiration: int = 3600) -> str:
        """Generate a presigned URL for an object in R2."""
        try:
            async with self.client as client:
                return await client.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={"Bucket": self._select_bucket(bucket_name), "Key": key},
                    HttpMethod="PUT",
                    ExpiresIn=expiration
                )
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error generating presigned URL: %s, key: %s", str(e), key)
            return ""
    async def update_metadata(self, key: str, metadata: Dict[Any, Any], bucket_name: str = "") -> bool:
        """Update metadata for an object in R2 without modifying the object content.
        
        Args:
            key: The key of the object
            metadata: New metadata to set
            bucket_name: Optional bucket name
            
        Returns:
            bool: True if successful, False otherwise
        """
        ret = False
        bucket = self._select_bucket(bucket_name)
        async with self.client as client:
            try:
                # Copy object to itself with new metadata
                response = await client.copy_object(
                    CopySource={'Bucket': bucket, 'Key': key},
                    Bucket=bucket,
                    Key=key,
                    Metadata=metadata,
                    MetadataDirective='REPLACE'  # This tells S3 to replace the metadata
                )
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    ret = True
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error updating metadata: %s, key: %s", str(e), key)
        return ret
