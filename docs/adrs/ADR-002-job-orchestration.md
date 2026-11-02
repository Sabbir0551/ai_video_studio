# ADR-002: Task Orchestration & Job Queue

## Status
Accepted

## Context
Video creation and multimodal video editing are long-running operations (from 15 seconds to several minutes). The orchestrator must support:
- Multi-stage pipeline execution (Ingest -> Script -> TTS -> Alignment -> Assembly -> Mix -> Render -> QA).
- Per-stage caching (avoid re-running unchanged steps).
- Progress reporting (% and stage description) via SSE/WebSocket.
- Resumability and error recovery with exponential backoff.
- Zero-friction single-user local installation on Windows, Linux, and macOS without mandatory external daemons.

## Decision
We implement a **Dual-Mode Queue Architecture**:
1. **Primary Default**: A lightweight, robust, thread/process-pool worker with SQLite persistence.
2. **Pluggable Scalability**: Redis + Celery/RQ driver behind the exact same `JobQueue` abstraction for distributed or containerized multi-worker deployments.

## Rationale
- Running Celery and Redis on local Windows requires installing and running a Redis server (often requiring WSL or Docker), adding unnecessary friction for a single-user studio.
- An SQLite-backed async queue with state machines (`PENDING`, `RUNNING`, `CHECKPOINT`, `COMPLETED`, `FAILED`, `CANCELLED`) provides immediate crash-resilience, ACID persistence, and zero setup dependencies.
- Any long job survives a server reboot; on restart, the queue checks for orphaned `RUNNING` jobs and resumes or fails gracefully.
