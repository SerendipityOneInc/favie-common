"""Prometheus Metrics"""
import logging
import os
from typing import Dict, List

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
DEFAULT_LATENCY_BUCKETS = [
    1.0, 3.0, 5.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 15.0, 20.0, 30.0, float("inf")
]
DEFAULT_COMMON_LABELS_KEYS = ["app_name", "host_name"]

class PrometheusMetrics:
    """Prometheus Metrics"""
    def __init__(
        self,
        app_name: str = None,
        latency_buckets: List[float] = None,
        common_labels_keys: List[str] = None
    ):
        self.app_name = app_name or os.getenv("APP_NAME", "unknown")
        self.host_name = os.getenv("HOSTNAME", "unknown")
        
        # 默认的buckets
        self.latency_buckets = latency_buckets or DEFAULT_LATENCY_BUCKETS
        
        # 通用标签
        self.common_labels_keys = common_labels_keys or DEFAULT_COMMON_LABELS_KEYS
        
        # 初始化指标
        self.downstream_request_time = Histogram(
            "downstream_request_duration_seconds",
            "Downstream service response time in seconds",
            ["workflow_name", "step", "status", "func_name"] + self.common_labels_keys,
            buckets=self.latency_buckets,
        )

        self.downstream_request_count = Counter(
            "downstream_request_count",
            "Number of requests made to downstream services",
            ["workflow_name", "step", "status", "func_name"] + self.common_labels_keys,
        )

        self.workflow_error_count = Counter(
            "workflow_error_total",
            "Total count of workflow errors",
            ["workflow_name", "step", "error_type", "func_name"] + self.common_labels_keys,
        )

    def get_common_labels(self) -> Dict[str, str]:
        return {
            "app_name": self.app_name,
            "host_name": self.host_name,
        }

    def safe_inc_error_count(
        self,
        workflow_name: str,
        step: str,
        error_type: str,
        func_name: str
    ):
        try:
            common_labels = self.get_common_labels()
            self.workflow_error_count.labels(
                workflow_name=workflow_name,
                step=step,
                error_type=error_type,
                func_name=func_name,
                **common_labels
            ).inc()
        except Exception as e:
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