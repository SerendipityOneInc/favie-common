"""metrics module"""
import functools
import logging
import os
import time
from typing import Dict, List, Optional

from prometheus_client import REGISTRY, Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics

logger = logging.getLogger(__name__)

class MetricsConfig:
    """Metrics config"""
    def __init__(
        self,
        latency_buckets: Optional[List[float]] = None,
    ):
        self.latency_buckets = latency_buckets or [
            0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")  # default buckets
        ]
        self.common_labels_keys = ["app_name", "host_name"]

class MetricsManager:
    """Metrics manager"""
    def __init__(self, config: MetricsConfig):
        self.config = config
        self.downstream_request_time = Histogram(
            "downstream_request_duration_seconds",
            "Downstream service response time in seconds",
            ["workflow_name", "step", "status", "func_name"] + config.common_labels_keys,
            buckets=config.latency_buckets,
        )
        
        self.downstream_request_count = Counter(
            "downstream_request_count",
            "Number of requests made to downstream services",
            ["workflow_name", "step", "status", "func_name"] + config.common_labels_keys,
        )
        
        self.workflow_error_count = Counter(
            "workflow_error_total",
            "Total count of workflow errors",
            ["workflow_name", "step", "error_type", "func_name"] + config.common_labels_keys,
        )

    def get_common_labels(self) -> Dict[str, str]:
        """get common labels"""
        return {
            "app_name": os.getenv("APP_NAME", "unknown"),
            "host_name": os.getenv("HOSTNAME", "unknown"),
        }
    
    def safe_inc_error_count(self, workflow_name: str, step: str, error_type: str, func_name: str):
        """safe increment error count"""
        try:
            common_labels = self.get_common_labels()
            self.workflow_error_count.labels(
                workflow_name=workflow_name, step=step, error_type=error_type, func_name=func_name, **common_labels
            ).inc()
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error(
                "Failed to increment error count: %s, labels: %s",
                e,
                {
                    "workflow_name": workflow_name,
                    "step": step,
                    "error_type": error_type,
                    "func_name": func_name,
                    **self.get_common_labels(),
                },
        )

    def track_function_metrics(self, workflow_name: str, step: str):
        """decorator: track downstream service call metrics"""
        common_labels = self.get_common_labels()

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    self.workflow_error_count.labels(
                        workflow_name=workflow_name,
                        step=step,
                        error_type=e.__class__.__name__,
                        func_name=func.__name__,
                        **common_labels
                    ).inc()
                    raise
                finally:
                    try:
                        status = "success" if success else "error"
                        self.downstream_request_count.labels(
                            workflow_name=workflow_name,
                            step=step,
                            status=status,
                            func_name=func.__name__,
                            **common_labels
                        ).inc()
                        self.downstream_request_time.labels(
                            workflow_name=workflow_name,
                            step=step,
                            status=status,
                            func_name=func.__name__,
                            **common_labels
                        ).observe(time.time() - start_time)
                    except Exception as metric_error: # pylint: disable=broad-exception-caught
                        logger.error("Failed to record metrics: %s", metric_error)
            return wrapper
        return decorator

    def init_metrics(self):
        """init metrics"""
        instrumentator = Instrumentator()

        # register custom metrics
        instrumentator.add(
            metrics.requests(
                metric_name="http_requests_total",
            should_include_handler=True,
            should_include_method=True,
                should_include_status=True,
            )
        )
        instrumentator.add(
            metrics.latency(
                metric_name="http_request_duration_seconds",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
                buckets=self.config.latency_buckets,
            )
        )
        instrumentator.add(
            metrics.request_size(
                metric_name="http_request_size_bytes",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
            )
        )

        # ensure custom metrics are registered
        for metric in [self.downstream_request_time, self.downstream_request_count, self.workflow_error_count]:
            if metric._name not in REGISTRY._names_to_collectors:
                REGISTRY.register(metric)

        return instrumentator
