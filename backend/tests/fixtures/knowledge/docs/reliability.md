# Reliability, retries, and observability

This document describes reliability practices: timeouts, retries with backoff, and
observability through structured logging and metrics.

## Timeouts and retries

Every outbound network call should set an explicit timeout. Transient failures are
retried with exponential backoff and jitter, up to a bounded retry count.

## Observability

Emit structured logs and metrics for important paths so on-call engineers retain
visibility. Removing logging reduces observability and should be reviewed carefully.
