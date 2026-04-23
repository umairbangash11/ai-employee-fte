"""Logic Orchestrator — AI-powered email triage and draft reply generation."""

__version__ = "0.1.0"

# Resilience module integration (Feature 015, T083)
from resilience import (
    CircuitBreaker,
    ExitCode,
    HealthManager,
    ResilienceError,
    RetryPolicy,
    ralph_wiggum_loop,
    route_to_failed_queue,
)
