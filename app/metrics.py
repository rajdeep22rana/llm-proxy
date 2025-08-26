from prometheus_client import (
    Counter,
    Histogram,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

registry = CollectorRegistry()

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    registry=registry,
)

# Provider-level metrics
provider_requests_total = Counter(
    "provider_requests_total",
    "Total provider calls by provider and operation",
    ["provider", "operation", "outcome"],
    registry=registry,
)

provider_request_duration_seconds = Histogram(
    "provider_request_duration_seconds",
    "Provider call latency in seconds",
    ["provider", "operation", "outcome"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    registry=registry,
)

__all__ = [
    "registry",
    "http_requests_total",
    "http_request_duration_seconds",
    "provider_requests_total",
    "provider_request_duration_seconds",
    "CONTENT_TYPE_LATEST",
    "generate_latest",
]
