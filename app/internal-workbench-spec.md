# Internal Workbench Specification

## Purpose

Specify a lightweight internal workbench that helps operate the first wedge
delivery system without overbuilding a product.

## Product Principle

The workbench should expose the minimum interface needed to run SEIS:

- diagnose a workflow
- score opportunity and risk
- manage delivery state
- collect evidence
- route approvals
- convert delivery records into assets

## Kernel/Shell Split

| Layer | Responsibility |
| --- | --- |
| SEIS kernel | Doctrine, wedge logic, delivery rules, evidence policy, approvals, asset conversion. |
| Workbench shell | Structured interface for humans to operate the kernel. |
| AI brains | Draft, analyze, audit, route, and summarize inside policy boundaries. |
| Human authority | Final approval for risk, claims, publication, production, and completion. |

## MVP Scope

- internal use only
- file-backed or repository-backed records at first
- no external customer login
- no autonomous production execution
- no broad provider orchestration
- no secret custody

## Readiness Gate

Implementation should wait until at least one real delivery loop has been
executed or internal use requires a lightweight operator surface. If built
earlier, it must remain a narrow internal prototype.
