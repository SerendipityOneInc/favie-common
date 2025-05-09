import json
import logging
import time
from functools import wraps
import inspect
from inspect import isasyncgenfunction, iscoroutinefunction, isgeneratorfunction
from typing import Any, AsyncIterator, Callable, Optional

from asyncstdlib import tee
from fastapi import Request
from opentelemetry import trace
from opentelemetry.context import Context, attach, create_key, get_current, set_value
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace.propagation import _SPAN_KEY, set_span_in_context
from opentelemetry.trace.span import Span
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)

handler = logging.StreamHandler()

formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelTraceSampled)s",
    rename_fields={
        "levelname": "severity",
        "asctime": "timestamp",
        "otelTraceID": "logging.googleapis.com/trace",
        "otelSpanID": "logging.googleapis.com/spanId",
        "otelTraceSampled": "logging.googleapis.com/trace_sampled",
    },
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

# file_handler = logging.FileHandler('app.log')
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

provider = TracerProvider(resource=Resource.create({"service.name": "favie-gateway"}), sampler=ALWAYS_ON)

cloud_trace_exporter = CloudTraceSpanExporter()
batch_processor = BatchSpanProcessor(cloud_trace_exporter, max_export_batch_size=10)
provider.add_span_processor(batch_processor)

# console_exporter = ConsoleSpanExporter()
# simple_processor_console = SimpleSpanProcessor(console_exporter)
# provider.add_span_processor(simple_processor_console)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)


def log_info(msg, *args, json_msg=None, **kwargs):
    """Log Info"""
    span = trace.get_current_span()
    extra = {
        "otelTraceID": format(span.get_span_context().trace_id, "032x"),
        "otelSpanID": format(span.get_span_context().span_id, "016x"),
        "otelTraceSampled": span.get_span_context().trace_flags.sampled,
        "json_fields": {"extra": json_msg or {}},
    }

    if "extra" in kwargs:
        kwargs["extra"].update(extra)
    else:
        kwargs["extra"] = extra

    logger.info(
        msg,
        *args,
        **kwargs,
    )


async def async_to_json_obj(arg, k=None, args=None):
    if isinstance(arg, AsyncIterator) and args != None and k != None:
        copy_arg, copy_arg2 = tee(arg, 2)
        args[k] = copy_arg2

        values = [value async for value in copy_arg]
        if values:
            return to_json_obj(values[-1])
        else:
            return ""
    else:
        return to_json_obj(arg)


def to_json_obj(arg):
    if isinstance(arg, BaseModel):
        try:
            result = json.loads(arg.model_dump_json())
        except Exception:
            result = ""
        return result
    elif isinstance(arg, (bool, int, float, str, list, tuple, set, dict)):
        return arg


async def async_set_stacktrace_input_meta(stack_trace, span: Span, args, kwargs, func, trace_input=False):
    if trace_input:
        inputs = {}

        signature = inspect.signature(func)
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        arguments = bound_arguments.arguments

        for k, arg in arguments.items():
            if k == "config":
                if arg.get("metadata"):
                    for meta_k, meta_v in arg.get("metadata").items():
                        span.set_attribute(meta_k, to_json_string(meta_v))
                continue
            if k == "context":
                continue
            inputs[k] = await async_to_json_obj(arg)

        # for idx, arg in enumerate(args):
        #     inputs[str(idx)] = await async_to_json_obj(arg, idx, args)
        # for k, arg in kwargs.items():
        #     if k == "config":
        #         if arg.get("metadata"):
        #             for meta_k, meta_v in arg.get("metadata").items():
        #                 span.set_attribute(meta_k, to_json_string(meta_v))
        #         continue
        #     if k == "context":
        #         continue
        #     inputs[k] = await async_to_json_obj(arg)
        stack_trace["input"] = inputs
        log_info("trace_log", json_msg=stack_trace)


def set_stacktrace_input_meta(stack_trace, span: Span, args, kwargs, func, trace_input=False):
    if trace_input:
        inputs = {}

        if func:

            signature = inspect.signature(func)
            bound_arguments = signature.bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            arguments = bound_arguments.arguments

            for k, arg in arguments.items():
                if k == "config":
                    if arg.get("metadata"):
                        for meta_k, meta_v in arg.get("metadata").items():
                            span.set_attribute(meta_k, to_json_string(meta_v))
                    continue
                if k == "context":
                    continue
                inputs[k] = to_json_obj(arg)
        else:
            
            for idx, arg in enumerate(args):
                inputs[str(idx)] = to_json_obj(arg)
            for k, arg in kwargs.items():
                if k == "config":
                    if arg.get("metadata"):
                        for meta_k, meta_v in arg.get("metadata").items():
                            span.set_attribute(meta_k, to_json_string(meta_v))
                    continue
                if k == "context":
                    continue
                inputs[k] = to_json_obj(arg)
        stack_trace["input"] = inputs
        log_info("trace_log", json_msg=stack_trace)


def set_stacktrace_output(
    stack_trace,
    span: Span,
    result,
    trace_output=False,
    is_output_error: Optional[Callable[[Any], bool]] = None,
):
    set_stacktrace_t = time.time()
    if is_output_error and is_output_error(result):
        span.set_attribute("output_error", int(is_output_error(result)))
    if trace_output:
        stack_trace["output"] = to_json_obj(result)
        if "input" in stack_trace:
            del stack_trace["input"]
        log_info("trace_log", json_msg=stack_trace)

    logger.info("set_stacktrace_output cost:%s", time.time() - set_stacktrace_t)


def context_trace(
    operation_name,
    inputs=None,
    output=None,
    is_output_error: Optional[Callable[[Any], bool]] = None,
    context=None,
):
    with tracer.start_as_current_span(
        operation_name,
        context=context if context else set_span_in_context(trace.get_current_span()),
    ) as span:
        stack_trace = {}
        if inputs:
            set_stacktrace_input_meta(stack_trace, span, [], inputs, None, True)

        set_stacktrace_output(stack_trace, span, output, True if output else False, is_output_error)


def get_context(args, kwargs):
    context = None
    for arg in args:
        if isinstance(arg, Request):
            context = extract(arg.headers)
            break

    for _, arg in kwargs.items():
        if isinstance(arg, Request):
            context = extract(arg.headers)
            break

    if not context:
        context = get_new_context()

    return context


def get_new_context():
    span = trace.get_current_span()

    if find_span(span, get_current()):
        context = set_span_in_context(span)
    else:
        context = set_span_in_context(span, context=set_value(create_key("current-span"), span))

    return context


def find_span(span, context: Context):
    for k, v in context.items():
        if k != _SPAN_KEY and v == span:
            return True
    return False


def end_span_recursive(span: ReadableSpan):
    c_span = span
    context = get_current()
    while c_span:
        if c_span.end_time is None:
            c_span.end()

        parent_context = c_span.parent
        if parent_context is None:
            break

        for k, span_item in context.items():
            if (
                k != _SPAN_KEY
                and isinstance(span_item, ReadableSpan)
                and span_item.get_span_context() == parent_context
            ):
                c_span = span_item
                continue


def context_trace_function(
    trace_name=None,
    trace_input=False,
    trace_output=False,
    is_output_error: Optional[Callable[[Any], bool]] = None,
    input_context=None,
    auto_end=True,
):
    def decorator(func):
        operation_name = trace_name if trace_name else func.__name__

        stack_trace = {"operation_name": operation_name}

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            args = list(args)
            context = input_context if input_context else get_context(args, kwargs)
            attach(context)
            with tracer.start_as_current_span(
                operation_name,
                context=context,
                end_on_exit=auto_end,
            ) as span:
                set_stacktrace_input_meta(stack_trace, span, args, kwargs, func, trace_input)

                result = func(*args, **kwargs)

                set_stacktrace_output(stack_trace, span, result, trace_output, is_output_error)

                return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            args = list(args)
            context = input_context if input_context else get_context(args, kwargs)
            attach(context)
            with tracer.start_as_current_span(
                operation_name,
                context=context,
                end_on_exit=auto_end,
            ) as span:
                await async_set_stacktrace_input_meta(stack_trace, span, args, kwargs, func, trace_input)

                result = await func(*args, **kwargs)

                set_stacktrace_output(stack_trace, span, result, trace_output, is_output_error)

                return result

        @wraps(func)
        def generator_wrapper(*args, **kwargs):
            args = list(args)
            context = input_context if input_context else get_context(args, kwargs)
            attach(context)
            with tracer.start_as_current_span(
                operation_name,
                context=context,
                end_on_exit=auto_end,
            ) as span:
                set_stacktrace_input_meta(stack_trace, span, args, kwargs, func, trace_input)

                result = None
                for value in func(*args, **kwargs):
                    result = value
                    yield value
                set_stacktrace_output(stack_trace, span, result, trace_output, is_output_error)

        @wraps(func)
        async def async_generator_wrapper(*args, **kwargs):
            args = list(args)
            context = input_context if input_context else get_context(args, kwargs)
            attach(context)
            with tracer.start_as_current_span(
                operation_name,
                context=context,
                end_on_exit=auto_end,
            ) as span:
                await async_set_stacktrace_input_meta(stack_trace, span, args, kwargs, func, trace_input)

                result = None
                async for value in func(*args, **kwargs):
                    result = value
                    yield value
                set_stacktrace_output(stack_trace, span, result, trace_output, is_output_error)

        if iscoroutinefunction(func):
            return async_wrapper
        elif isgeneratorfunction(func):
            return generator_wrapper
        elif isasyncgenfunction(func):
            return async_generator_wrapper
        else:
            return sync_wrapper

    return decorator


def clean_empty(d):
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary."""
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v != [] and v is not None]
    return {k: v for k, v in ((k, clean_empty(v)) for k, v in d.items()) if v is not None and v != {}}


def custom_serializer(obj):
    """Fallback function to convert unserializable objects."""
    if hasattr(obj, "__dict__"):
        # Attempt to serialize custom objects by their __dict__ attribute.
        return clean_empty(obj.__dict__)
    else:
        # For other types, just convert to string
        return str(obj)


def to_string(any_object):
    """Converts any object to a JSON-parseable string, omitting empty or None values."""
    if isinstance(any_object, str):
        return any_object
    # cleaned_object = clean_empty(any_object)
    try:
        json_str = json.dumps(any_object, indent=2)
        return json_str
    except Exception:
        return any_object


def to_json_string(any_object):
    """Converts any object to a JSON-parseable string, omitting empty or None values."""
    if isinstance(any_object, str):
        return any_object
    cleaned_object = clean_empty(any_object)
    return json.dumps(cleaned_object, default=custom_serializer, indent=2)
