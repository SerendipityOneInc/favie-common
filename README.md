# Favie Common

Favie Common provides shared utilities used across Favie services. It offers wrappers for caching, database access, tracing, metrics and FastAPI middleware.

## Installation

```bash
poetry add favie-common
# or
pip install favie-common
```

## Modules

### Cache (`favie_common.cache`)
- **RedisWrapper** – asynchronous wrapper over `redis.asyncio`.
  - Automatically connects using `REDIS_URL` and `REDIS_AUTH_STRING`.
  - Methods: `get`, `set`, `setnx`, `delete`, `lrange`, `lpush`, `close`.
  - Exposes a ready-to-use `redis` instance.

### Database (`favie_common.database`)
- **AsyncMongoDBWrapper** – async helper around `motor` for MongoDB.
  - CRUD helpers (`create`, `create_many`, `read`, `read_one`, `read_by_id`).
  - Update helpers (`update`, `upsert_document`, `update_by_id`, `replace_one`).
  - Deletion helpers (`delete`, `delete_by_id`, `delete_collection`).
  - Utility methods `get_all`, `get_total_count`, `get_random_one`.
  - Automatically manages `created_at` and `updated_at` timestamps.
  - `mongo` instance configured via environment variables (`MONGODB_USER`, `MONGODB_PASSWORD`, `MONGODB_HOST`, `MONGODB_APP_NAME`, `MONGODB_NAME`).

- **R2Client** – Cloudflare R2 object storage client using `aioboto3`.
  - Singleton implementation ensuring one client per process.
  - Upload methods: `upload_file`, `upload_fileobj`, `upload_object` (supports metadata).
  - Download methods: `download_file`, `download_object`.
  - Utility helpers: `check_object_exists`, `get_object_size`, `get_object_with_width_height`, `generate_presigned_url`, `update_metadata`.

- **R2** – legacy simplified wrapper providing `upload_file`, `upload_fileobj` and `download_file`.

### Metrics (`favie_common.metrics`)
- **PrometheusMetrics** – integrates `prometheus_fastapi_instrumentator`.
  - `init_metrics(app)` instruments a FastAPI app and exposes metrics on `/admin/metrics`.
  - Histograms and counters for downstream requests: `downstream_request_time`, `downstream_request_count`, `workflow_error_count`.
  - `track_function_metrics` decorator records call counts and durations.
  - Safe increment helpers to avoid exceptions in metrics code.

### Middleware (`favie_common.middleware`)
- **AuthMiddleware** – validates an `Authorization` header via the user service and stores user info on the request.
- **AuthDependency** and `auth_dependency_no_raise_error` – endpoint level dependencies for authentication.
- **HttpLoggingMiddleware** – logs request/response metadata and latency.
- **register_exception_handlers** – attaches a default exception handler returning HTTP 500 with structured logs.

### Trace (`favie_common.trace`)
- Utilities built on OpenTelemetry for structured tracing and logging.
- `context_trace_function` decorator propagates context and records span input/output automatically.
- Logging helper `log_info` injects trace IDs into log records.
- Helper functions like `to_string` and `to_json_string` convert objects for trace logs.

## Development

Run tests using:

```bash
pytest -q
```

Code style is enforced via `black`, `isort` and `autoflake` using pre-commit:

```bash
pre-commit run --files <changed files>
```

