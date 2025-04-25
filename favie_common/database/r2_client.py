"""
This is a wrapper around aioboto3 to make it easier to upload and download files to R2.
"""
from aioboto3 import Session
from botocore.client import Config
import logging
from typing import Optional, Dict, Any, Tuple
from trace.context_trace_func import context_trace_function
from metrics.prometheus_metrics import PrometheusMetrics

logger = logging.getLogger(__name__)


LATENCY_BUCKETS = [
    0.025,  # 25ms
    0.05,  # 50ms
    0.075,  # 75ms
    0.1,  # 100ms
    0.25,  # 250ms
    0.5,  # 500ms
    0.75,  # 750ms
    1.0,  # 1s
    1.25,  # 1.25s
    1.5,  # 1.5s
    1.75,  # 1.75s
    2.0,  # 2s
    2.5,  # 2.5s
    3.0,  # 3s
    3.5,  # 3.5s
    4.0,  # 4s
    4.5,  # 4.5s
    5.0,  # 5s
    5.5,  # 5.5s
    6.0,  # 6s
    6.5,  # 6.5s
    7.0,  # 7s
    8.0,  # 8s
    9.0,  # 9s
    10.0,  # 10s
    10.5,  # 10.5s
    float("inf"),
]

r2_client_metrics = PrometheusMetrics(LATENCY_BUCKETS)

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

    @context_trace_function(trace_name="initialize_client")
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

    @context_trace_function(trace_name="upload_file")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="upload_file")
    async def upload_file(self, key: str, filename: str, extra_args: Optional[Dict[Any, Any]] = None):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_file(Filename=filename, Bucket=self.bucket_name, Key=key, ExtraArgs=extra_args or {})

    @context_trace_function(trace_name="upload_fileobj")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="upload_fileobj")
    async def upload_fileobj(self, fileobj, key: str, extra_args: Optional[Dict[Any, Any]] = None):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_fileobj(Fileobj=fileobj, Bucket=self.bucket_name, Key=key, ExtraArgs=extra_args or {})

    @context_trace_function(trace_name="download_file")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="download_file")
    async def download_file(self, key: str, filename: str):
        """Download file from R2."""
        async with self.client as client:
            await client.download_file(Bucket=self.bucket_name, Key=key, Filename=filename)

    @context_trace_function(trace_name="upload_object")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="upload_object")
    async def upload_object(self, fileobj, key: str, bucket_name: str = "",
                        metadata: Optional[Dict[Any, Any]] = None):
        """Upload file to R2.
        
        Args:
            fileobj: The file object to upload
            key: The key to store the file under in R2
            bucket_name: Optional bucket name, defaults to instance bucket_name
            extra_args: Optional extra arguments for upload
            metadata: Optional metadata dictionary to attach to the object
        """
        async with self.client as client:
            await client.put_object(
                Bucket=bucket_name or self.bucket_name, 
                Key=key,
                Body=fileobj,
                Metadata=metadata or {}
            )

    @context_trace_function(trace_name="download_object")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="download_object")
    async def download_object(self, key: str, bucket_name: str = "") -> Optional[bytes]:
        """Download file from R2.
        
        Args:
            key: The key of the file in R2
        
        Returns:
            bytes of the file content
        """
        async with self.client as client:
            try:
                response = await client.get_object(Bucket=bucket_name or self.bucket_name, Key=key)
                return await response["Body"].read()
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.error("Error downloading file: %s, key: %s", str(e), key)
                return None
    
    @context_trace_function(trace_name="check_object_exists")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="check_object_exists")
    async def check_object_exists(self, key: str) -> bool:
        """Check if an object exists in R2."""
        async with self.client as client:
            try:
                response = await client.head_object(Bucket=self.bucket_name, Key=key)
                return response["ResponseMetadata"]["HTTPStatusCode"] == 200
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.warning("Error checking object exists: %s, key: %s", str(e), key)
                return False

    @context_trace_function(trace_name="get_object_size")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="get_object_size")
    async def get_object_size(self, key: str) -> int:
        """Get the size of an object in R2."""
        try:
            async with self.client as client:
                response = await client.head_object(Bucket=self.bucket_name, Key=key)
                return response["ContentLength"]
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error getting object size: %s, key: %s", str(e), key)
            return 0
        
    @context_trace_function(trace_name="get_object_with_width_height")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="get_object_with_width_height")
    async def get_object_with_width_height(self, key: str) -> Tuple[float, float]:
        """Get the object with width and height."""
        try:
            async with self.client as client:
                response = await client.head_object(Bucket=self.bucket_name, Key=key)
                image_width = float(response.get("Metadata", {}).get("image_width", 0.0))
                image_height = float(response.get("Metadata", {}).get("image_height", 0.0))
                return image_width, image_height
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error getting object with width and height: %s, key: %s", str(e), key)
            return 0, 0

    @context_trace_function(trace_name="list_objects")
    @r2_client_metrics.track_function_metrics(workflow_name="r2_client", step="list_objects")
    async def generate_presigned_url(self, key: str, bucket_name: str = "", expiration: int = 3600) -> str:
        """Generate a presigned URL for an object in R2."""
        try:
            async with self.client as client:
                return await client.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={"Bucket": bucket_name or self.bucket_name, "Key": key},
                    HttpMethod="PUT",
                    ExpiresIn=expiration
                )
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.warning("Error generating presigned URL: %s, key: %s", str(e), key)
            return ""
