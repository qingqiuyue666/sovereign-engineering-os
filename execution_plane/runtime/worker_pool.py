"""Bounded worker pool for adapter jobs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import BoundedSemaphore
from typing import Any

from execution_plane.runtime.token_policy import normalize_runtime_policy

JobCallable = Callable[[], dict[str, Any]]


def run_bounded_jobs(
    jobs: Sequence[Mapping[str, Any]],
    token: Mapping[str, Any],
    dispatch: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    policy = normalize_runtime_policy(token)
    concurrency = policy["concurrency"]
    global_limit = int(concurrency["max_global_jobs"])
    per_adapter_limits = {
        str(adapter): int(limit)
        for adapter, limit in dict(concurrency["max_per_adapter_jobs"]).items()
    }
    semaphores = {
        adapter: BoundedSemaphore(limit)
        for adapter, limit in per_adapter_limits.items()
    }

    def run_one(job: Mapping[str, Any]) -> dict[str, Any]:
        adapter = str(job.get("adapter", ""))
        semaphore = semaphores.get(adapter, BoundedSemaphore(1))
        with semaphore:
            return dispatch(job)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=global_limit) as executor:
        futures = [executor.submit(run_one, job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    return results
