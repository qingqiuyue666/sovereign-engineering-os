# Tool Selection Gate

## Purpose

Prevent tool hoarding and dependency sprawl. A tool is useful only when it
reduces the current bottleneck at an acceptable maintenance and integration
cost.

## Gate Questions

1. What is the current bottleneck?
2. Does a built-in repository capability or local command already solve it?
3. Does the new tool reduce human labor now?
4. What maintenance cost does it add?
5. What integration cost does it add?
6. Does it introduce new permissions, services, credentials, network access, or
   operational dependencies?
7. Is it needed for this task, or only interesting for later?

## Classification

## Use Now

Use now only when the tool is needed for the current bottleneck, does not cross
a high-risk gate, and reduces work more than it adds operational burden.

## Later

Defer when the tool is plausible but the current task can be completed without
it.

## Reference Only

Keep as a reference when it informs design but should not be installed,
configured, or integrated.

## Reject

Reject when the tool duplicates existing capability, increases risk, adds
unclear maintenance load, requires unapproved permissions, or distracts from
the current scope.

## Rule

Do not install a GitHub repo, skill, agent, service, dependency, or framework
just because it exists.
