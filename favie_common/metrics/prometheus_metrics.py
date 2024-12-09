import functools
import logging
import os
import time
from typing import Dict

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
get_common_labels_keys = ["app_name", "host_name"]



def get_common_labels() -> Dict[str, str]:
    return {
        "app_name": os.getenv("APP_NAME", "unknown"),
        "host_name": os.getenv("HOSTNAME", "unknown"),
    }


from prometheus_client import REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator, metrics


class PrometheusMetrics:
    def __init__(self, buckets: list[float] = []) -> None:
        self.buckets = buckets

        self.downstream_request_time = Histogram(
            "downstream_request_duration_seconds",
            "Downstream service response time in seconds",
            ["workflow_name", "step", "status", "func_name"] + get_common_labels_keys,
            **({"buckets": self.buckets} if self.buckets else {}),
        )

        self.downstream_request_count = Counter(
            "downstream_request_count",
            "Number of requests made to downstream services",
            ["workflow_name", "step", "status", "func_name"] + get_common_labels_keys,
        )

        self.workflow_error_count = Counter(
            "workflow_error_total",
            "Total count of workflow errors",
            ["workflow_name", "step", "error_type", "func_name"] + get_common_labels_keys,
        )

    def init_metrics(self, app):
        instrumentator = Instrumentator()

        # 注册自定义指标
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
                **({"buckets": self.buckets} if self.buckets else {}),
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

        # 确保自定义指标被注册
        for metric in [self.downstream_request_time, self.downstream_request_count, self.workflow_error_count]:
            if metric._name not in REGISTRY._names_to_collectors:
                REGISTRY.register(metric)

        instrumentator.instrument(app).expose(app, endpoint="/admin/metrics")
        return instrumentator


    def safe_inc_error_count(self, workflow_name: str, step: str, error_type: str, func_name: str, n: int = 1):
        """Increment error count"""
        try:
            common_labels = get_common_labels()
            self.workflow_error_count.labels(
                workflow_name=workflow_name, step=step, error_type=error_type, func_name=func_name, **common_labels
            ).inc(n)
        except Exception as e:
            logger.error(
                "Failed to increment error count: %s, labels: %s",
                e,
                {
                    "workflow_name": workflow_name,
                    "step": step,
                    "error_type": error_type,
                    "func_name": func_name,
                    **get_common_labels(),
                },
            )
    def safe_inc_downstream_request_count(self, workflow_name: str, step: str, status: str, func_name: str, n: int = 1):
        """Increment downstream request count"""
        try:
            common_labels = get_common_labels()
            self.downstream_request_count.labels(
                workflow_name=workflow_name, step=step, status=status, func_name=func_name, **common_labels
            ).inc(n)
        except Exception as e:
            logger.error("Failed to increment downstream request count: %s, labels: %s", e, locals())


    def track_function_metrics(self, workflow_name: str, step: str):
        """
        Decorator:用于跟踪下游服务调用的指标
        支持同步和异步函数
        """
        common_labels = get_common_labels()

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                result = None
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                except Exception:
                    raise
                finally:
                    try:
                        status = "success" if success else "error"
                        self.downstream_request_count.labels(
                            workflow_name=workflow_name, step=step, status=status, func_name=func.__name__, **common_labels
                        ).inc()
                        self.downstream_request_time.labels(
                            workflow_name=workflow_name, step=step, status=status, func_name=func.__name__, **common_labels
                        ).observe(time.time() - start_time)
                    except Exception as metric_error:
                        logger.error(f"Failed to record metrics: {metric_error}, labels: {locals()}")

            return wrapper

        return decorator
