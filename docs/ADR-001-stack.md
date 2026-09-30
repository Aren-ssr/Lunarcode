# ADR-001: A Python-first web application

**Status:** Accepted for the first version  
**Date:** 2026-09-30  
**Decider:** Project owner, with implementation choice delegated to the technical lead

## Context

The project owner is learning backend development with Python and asked for a working first version with accounts, SQL persistence, lessons, progress, and a modern animated interface. The current machine has Python and Node.js, but npm and Docker are unavailable. The first local setup should therefore avoid requiring a JavaScript package manager or a database server.

## Decision

Use FastAPI for the server, Jinja templates for page rendering, browser JavaScript and CSS for interaction and visual effects, and SQLAlchemy for data access. Use SQLite locally and allow PostgreSQL through DATABASE_URL for hosting.

## Options considered

### Python-first server-rendered app

- Complexity: low to moderate
- Local setup: Python virtual environment and pip only
- Learning fit: strong connection to Python backend concepts
- Trade-off: the browser interface is less component-driven than a React application

### Separate React and API services

- Complexity: moderate to high
- Local setup: also requires npm and separate frontend/backend processes
- Learning fit: covers more tools at once
- Trade-off: adds setup and deployment work before the course product is proven

## Consequences

- The project can run on this machine without npm or Docker.
- CSS supplies the 3D lunar visual treatment; small JavaScript behaviors handle tabs, the language selector, copy buttons, and the trial clock.
- SQLAlchemy keeps the app compatible with SQLite and PostgreSQL using a connection URL.
- A separate React frontend can be considered later if interactive course authoring or richer client-side behavior outgrows server-rendered pages.
