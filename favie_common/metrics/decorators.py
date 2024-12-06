"""Metrics Decorators"""
import functools
import logging
import time

from favie_common.metrics.prometheus_metrics import PrometheusMetrics

logger = logging.getLogger(__name__)

def track_function_metrics(
    metrics: PrometheusMetrics,
    workflow_name: str,
    step: str,
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception:
                raise
            finally:
                try:
                    status = "success" if success else "error"
                    common_labels = metrics.get_common_labels()
                    
                    metrics.downstream_request_count.labels(
                        workflow_name=workflow_name,
                        step=step,
                        status=status,
                        func_name=func.__name__,
                        **common_labels
                    ).inc()
                    
                    metrics.downstream_request_time.labels(
                        workflow_name=workflow_name,
                        step=step,
                        status=status,
                        func_name=func.__name__,
                        **common_labels
                    ).observe(time.time() - start_time)
                except Exception as metric_error:
                    logger.error(f"Failed to record metrics: {metric_error}, labels: {locals()}")
        return wrapper
    return decorator