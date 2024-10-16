from aioboto3 import Session
from botocore.client import Config


class R2:
    """Object storage client."""

    _instance = None

    def __new__(
        cls, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str, region_name: str = "auto"
    ):
        if cls._instance is None:
            cls._instance = super(R2, cls).__new__(cls)
            cls._instance._initialize(endpoint_url, access_key_id, secret_access_key, bucket_name, region_name)
        return cls._instance

    def _initialize(
        self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str, region_name: str
    ):
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize R2 client."""
        session = Session()
        return session.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name=self.region_name,
        )

    async def upload_file(self, key: str, filename: str, extra_args: dict = None):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_file(Filename=filename, Bucket=self.bucket_name, Key=key, ExtraArgs=extra_args)

    async def upload_fileobj(self, fileobj, key: str, extra_args: dict = None):
        """Upload file to R2."""
        async with self.client as client:
            await client.upload_fileobj(Fileobj=fileobj, Bucket=self.bucket_name, Key=key, ExtraArgs=extra_args)

    async def download_file(self, key: str, filename: str):
        """Download file from R2."""
        async with self.client as client:
            await client.download_file(Bucket=self.bucket_name, Key=key, Filename=filename)
