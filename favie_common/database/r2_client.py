"""
This is a wrapper around aioboto3 to make it easier to upload and download files to R2.
"""
from aioboto3 import Session
from botocore.client import Config
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class R2Client:
    """Object storage client for Cloudflare R2.
    
    This is a singleton wrapper around aioboto3 to make it easier to upload and download files to R2.
    The client uses S3-compatible API to interact with Cloudflare R2 storage service.
    
    Features:
    - Singleton pattern ensures only one instance per process
    - Async support using aioboto3
    - Multiple upload/download methods for different use cases
    - Metadata support for objects
    - Presigned URL generation
    - Object existence checking and size retrieval
    """

    _instance = None

    def __new__(
        cls, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str="", region_name: str = "auto", config: Config = Config(signature_version="s3v4")
    ):
        """Create or return existing R2Client instance (Singleton pattern).
        
        Args:
            endpoint_url: R2 endpoint URL (e.g., 'https://xxx.r2.cloudflarestorage.com')
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: Default bucket name for operations
            region_name: AWS region name, defaults to 'auto' for R2
            config: Boto3 client configuration
            
        Returns:
            R2Client: Singleton instance of the client
        """
        if cls._instance is None:
            cls._instance = super(R2Client, cls).__new__(cls)
            cls._instance._initialize(endpoint_url, access_key_id, secret_access_key, bucket_name, region_name, config)
        return cls._instance

    def _initialize(
        self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str, region_name: str, config: Config
    ):
        """Initialize the R2Client instance with connection parameters.
        
        Args:
            endpoint_url: R2 endpoint URL
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: Default bucket name
            region_name: AWS region name
            config: Boto3 client configuration
        """
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.config = config

    @property
    def client(self):
        """Get a new aioboto3 S3 client instance.
        
        Creates a new client instance each time it's accessed to ensure thread safety
        and avoid connection pooling issues.
        
        Returns:
            aioboto3.Session.client: Configured S3 client for R2
        """
        return self._initialize_client()

    def _initialize_client(self):
        """Initialize and configure the aioboto3 S3 client for R2.
        
        Returns:
            aioboto3.Session.client: Configured S3 client with R2 credentials and settings
        """
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
        """Select which bucket to use for the operation.
        
        Args:
            bucket_name: Optional bucket name to use for this operation
            
        Returns:
            str: The bucket name to use (provided bucket or default instance bucket)
        """
        if bucket_name:
            return bucket_name
        return self.bucket_name

    async def upload_file(self, key: str, filename: str, extra_args: Optional[Dict[Any, Any]] = None, bucket_name: str = ""):
        """Upload file to R2 from local file path.
        
        This method uploads a file by reading from a local file path using aioboto3's upload_file method.
        Best for uploading existing files on disk.
        
        Args:
            key: The S3 key (object name) to store the file under
            filename: Local file path to upload
            extra_args: Optional extra arguments for upload (e.g., ContentType, ACL)
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Differences from other upload methods:
        - upload_file: Reads from local file path (this method)
        - upload_fileobj: Reads from file-like object in memory
        - upload_object: Uses put_object API, allows metadata, more control
        """
        async with self.client as client:
            await client.upload_file(Filename=filename, Bucket=self._select_bucket(bucket_name), Key=key, ExtraArgs=extra_args or {})

    async def upload_fileobj(self, fileobj, key: str, extra_args: Optional[Dict[Any, Any]] = None, bucket_name: str = ""):
        """Upload file to R2 from file-like object.
        
        This method uploads a file from a file-like object (e.g., BytesIO, opened file) 
        using aioboto3's upload_fileobj method. Best for uploading data already in memory.
        
        Args:
            fileobj: File-like object to upload (e.g., BytesIO, file handle)
            key: The S3 key (object name) to store the file under
            extra_args: Optional extra arguments for upload (e.g., ContentType, ACL)
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Differences from other upload methods:
        - upload_file: Reads from local file path
        - upload_fileobj: Reads from file-like object in memory (this method)
        - upload_object: Uses put_object API, allows metadata, more control
        """
        async with self.client as client:
            await client.upload_fileobj(Fileobj=fileobj, Bucket=self._select_bucket(bucket_name), Key=key, ExtraArgs=extra_args or {})

    async def download_file(self, key: str, filename: str, bucket_name: str = ""):
        """Download file from R2 to local file path.
        
        This method downloads a file and saves it directly to a local file path
        using aioboto3's download_file method. Best for saving files to disk.
        
        Args:
            key: The S3 key (object name) to download
            filename: Local file path where the downloaded file will be saved
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Differences from other download methods:
        - download_file: Downloads and saves to local file path (this method)
        - download_object: Downloads and returns file content as bytes in memory
        """
        async with self.client as client:
            await client.download_file(Bucket=self._select_bucket(bucket_name), Key=key, Filename=filename)

    async def upload_object(self, fileobj, key: str, bucket_name: str = "", metadata: Optional[Dict[Any, Any]] = None) -> bool:
        """Upload file to R2 using put_object API with metadata support.
        
        This method uses the lower-level put_object API which provides more control
        and allows setting custom metadata. Returns success status.
        
        Args:
            fileobj: The file object/bytes to upload
            key: The S3 key (object name) to store the file under
            bucket_name: Optional bucket name, defaults to instance bucket_name
            metadata: Optional metadata dictionary to attach to the object
            
        Returns:
            bool: True if upload successful, False otherwise
            
        Differences from other upload methods:
        - upload_file: Reads from local file path, uses upload_file API
        - upload_fileobj: Reads from file-like object, uses upload_fileobj API  
        - upload_object: Uses put_object API, supports metadata, returns success status (this method)
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
        """Download file from R2 and return as bytes.
        
        This method downloads a file and returns its content as bytes in memory
        using the get_object API. Best for processing file content directly without saving to disk.
        
        Args:
            key: The S3 key (object name) to download
            bucket_name: Optional bucket name, defaults to instance bucket_name
        
        Returns:
            bytes: File content as bytes, or None if download failed
            
        Differences from other download methods:
        - download_file: Downloads and saves to local file path
        - download_object: Downloads and returns file content as bytes in memory (this method)
        """
        async with self.client as client:
            try:
                response = await client.get_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return await response["Body"].read()
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.error("Error downloading file: %s, key: %s", str(e), key)
                return None
    
    async def check_object_exists(self, key: str, bucket_name: str = "") -> bool:
        """Check if an object exists in R2 storage.
        
        Uses the head_object API call to check for object existence without downloading content.
        This is more efficient than trying to download the object.
        
        Args:
            key: The S3 key (object name) to check
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Returns:
            bool: True if object exists, False otherwise
        """
        async with self.client as client:
            try:
                response = await client.head_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return response["ResponseMetadata"]["HTTPStatusCode"] == 200
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.warning("Error checking object exists: %s, key: %s", str(e), key)
                return False

    async def get_object_size(self, key: str, bucket_name: str = "") -> int:
        """Get the size of an object in R2 storage.
        
        Uses head_object to retrieve object metadata including size without downloading content.
        
        Args:
            key: The S3 key (object name) to get size for
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Returns:
            int: Size of the object in bytes, 0 if object doesn't exist or error occurs
        """
        try:
            async with self.client as client:
                response = await client.head_object(Bucket=self._select_bucket(bucket_name), Key=key)
                return response["ContentLength"]
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error getting object size: %s, key: %s", str(e), key)
            return 0
        
    async def get_object_with_width_height(self, key: str, bucket_name: str = "") -> Tuple[float, float]:
        """Get image dimensions from object metadata.
        
        Retrieves image width and height from custom metadata stored with the object.
        The metadata keys expected are 'image_width' and 'image_height'.
        
        Args:
            key: The S3 key (object name) of the image
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Returns:
            Tuple[float, float]: (width, height) in pixels, (0, 0) if not found or error
        """
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
        """Generate a presigned URL for uploading objects to R2.
        
        Creates a temporary URL that allows uploading to the specified key without exposing credentials.
        Useful for client-side uploads or temporary access.
        
        Args:
            key: The S3 key (object name) where the file will be uploaded
            bucket_name: Optional bucket name, defaults to instance bucket_name
            expiration: URL expiration time in seconds, defaults to 1 hour (3600s)
            
        Returns:
            str: Presigned URL for PUT operation, empty string if generation fails
            
        Note:
            The generated URL is for PUT operations (uploads). For download URLs,
            you would need to modify the ClientMethod parameter.
        """
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
        """Update metadata for an existing object in R2 without modifying the object content.
        
        Uses the copy_object operation to copy the object to itself with new metadata.
        This is the standard S3-compatible way to update metadata without changing content.
        
        Args:
            key: The S3 key (object name) of the existing object
            metadata: New metadata dictionary to set (will replace existing metadata)
            bucket_name: Optional bucket name, defaults to instance bucket_name
            
        Returns:
            bool: True if metadata update successful, False otherwise
            
        Note:
            This operation will replace ALL existing metadata with the provided metadata.
            If you want to preserve some existing metadata, you need to include it in the
            metadata parameter.
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
