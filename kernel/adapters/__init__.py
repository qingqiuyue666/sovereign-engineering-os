"""Real-model adapters conforming to `kernel.services.inference_service.ModelAdapter`.

Adapters live OUTSIDE the kernel service layer. They are workers, not
authority. They must never mutate ledger state and must normalize every
provider-specific failure mode to a small set of governed failure
classes that the inference service already knows how to route through
`_emit_failure_bundle`.

This package currently contains exactly one adapter (by design for the
phase-1 ignition tracer):

- `anthropic_adapter.AnthropicMessagesAdapter` — Anthropic Messages API
  (`POST https://api.anthropic.com/v1/messages`).
"""
