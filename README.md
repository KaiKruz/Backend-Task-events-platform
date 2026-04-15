# Backend Task

Backend service workspace.

## What’s in this repo

- `SPEC.md`: requirements and acceptance criteria (edit this first)
- `AGENTS.md`: working rules for humans/agents
- `.cursor/rules/backend-task.mdc`: Cursor-specific repo rules

## Quickstart

This project scaffold is intentionally stack-agnostic. Once you add the actual backend implementation, update this section with:

- Prerequisites (runtime + version)
- Install steps
- How to run locally
- How to run tests
- Environment variables (`.env.example`, never real secrets)

## Common expectations (recommended)

- Health endpoint: `GET /health` → `200 { "status": "ok" }`
- Consistent error envelope across APIs
- Input validation at boundaries
- Structured logs where practical

