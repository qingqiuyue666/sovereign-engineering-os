# AI Brain Routing Spec

## Purpose

Define how the workbench should route AI assistance without treating one
model as the strategy.

## Brain Types

| Brain | Use | Boundary |
| --- | --- | --- |
| Strategic brain | Wedge, buyer, control-point, and productization reasoning. | Cannot certify market proof. |
| Engineering brain | Workflow and technical analysis. | Requires review for material risk. |
| Auditor brain | Claim, evidence, limitation, and risk review. | Must be separate from executor when risk is material. |
| Production brain | Drafts templates, reports, outreach, and artifacts. | Cannot approve final claims. |
| Worker brain | Performs bounded low-risk formatting or extraction. | No final authority. |
| Local/private brain | Handles sensitive local context inside boundaries. | No external transmission without approval. |

## Routing Rules

- AI output is a claim until verified.
- Material claims require auditor review.
- External claims require human approval.
- Provider choice must remain replaceable.
- Low-tier worker output cannot become final strategy, architecture, risk,
  completion, or market-selection decision.

## Boundary

This spec does not build a router or integrate providers. It defines the
future app rule set.
