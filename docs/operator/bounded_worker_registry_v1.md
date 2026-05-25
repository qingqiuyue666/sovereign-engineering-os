# Bounded Worker Registry V1

## Scope

Bounded Worker Registry V1 declares Codex, Claude, Gemini, GPT, DeepSeek, and
local deterministic Python as worker types for future planning and routing
artifacts.

## Boundary

This is a declaration layer only. It does not call providers, store
credentials, execute tools, dispatch workers, launch browsers, access networks,
or grant production autonomy.

## Worker Contract

Each worker declaration includes:

- worker id and display name
- provider family
- task classes
- input and output contract fields
- timeout metadata
- budget metadata
- evidence requirements
- hallucination boundary rules
- false live-provider, credential, tool-execution, and autonomy flags

## Routing Plan Artifact

Routing plans list candidate worker ids for a task class and rejected worker ids
for transparency. Routing plans are non-executing artifacts and record that no
dispatch, provider call, credential access, or tool execution occurred.
