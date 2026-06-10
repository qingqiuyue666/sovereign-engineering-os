# Operator Console State Model V1

## Purpose

Define the user-facing cockpit state model without building a UI runtime.

## Architecture

The model enumerates required panels, allowed structured action types, forbidden
UI payload fields, and candidate UI shell metadata. A future UI can consume this
state model, but this PR does not create Tauri, Electron, PySide, a web server,
or a frontend project.

## Allowed UI actions

The UI may submit only structured `task_intent`, `command_id`,
`approval_decision`, `risk_acknowledgement`, `replay_request`, `asset_query`, and
`workflow_selection` actions.

## Safety boundaries

UI actions cannot submit raw commands, command lines, arbitrary argv,
executable paths, cwd/env/path overrides, direct tool launches, direct file
writes, network calls, browser calls, provider calls, credentials, or secrets.

## Tauri status

Tauri is listed as a candidate future desktop shell only. No dependency,
frontend, Rust project, runtime integration, or launch path is added.
