# AWS Strands Multi-Agent Architecture – Lufthansa Inspiria

## Goals

- Deliver a Lufthansa-branded inspirational assistant capable of:
  - resolving natural-language itineraries,
  - fetching live fares (via Google Flights/Calendar/Explore),
  - surfacing destination intel (weather, highlights, reasons to travel),
  - and responding in the personas already exposed through the **Paul/Gina/Bianca** UIs.
- Achieve this through three Strands agents that coordinate via a supervisor graph, so we can grow capabilities without frequently publishing new Bedrock Agent versions.
- Reuse all microservices we already run (proxy, google-api, antiPhaser, derDrucker) and the existing React single-page UIs.

## High-Level Components

| Agent | Purpose | Model(s) | Tools |
|-------|---------|----------|-------|
| Supervisor (`conductor`) | Session memory, reasoning, orchestration, final draft | Bedrock **Claude 3.5 Sonnet** (primary), fallback **Amazon Nova Lite** | AWS Strands built-ins (tool routing, memory, `current_time`), external IATA lookup (public REST API via `http_request`), Flight Search agent, Destination Scout agent |
| Flight Search Agent (`flight_orca`) | Flight availability & price search | Bedrock **Llama 3.1 70B Instruct** (lightweight reasoning around tool outputs) | `google/flights/search`, `google/calendar/search`, `google/explore/search`, `derDrucker` |
| Destination Scout Agent (`scout`) | Destination inspiration, weather, events | Bedrock **Nova Micro** (fast) + optional **Claude 3 Haiku** | SearchAPI (Google Travel Explore), Open-Meteo, Wikipedia/Tripadvisor scrapers |

### Data Flow

1. UI (Paul/Gina/Bianca) → proxy (`proxy.mjs`) → **Supervisor agent** (`InvokeStrandsSupervisor`).
2. Supervisor normalises user input (lat/lon → IATA via a public API, time phrases via model+`current_time`) and decides:
   - If itinerary is well specified ⇒ call Flight Search agent.
   - If user is undecided or missing parameters ⇒ call Destination Scout first, or `google/explore` via Flight Search agent in "explore" mode.
3. Flight Search agent returns structured offers + metadata (calendars, alternatives). Supervisor validates + crafts final persona-specific copy.
4. Destination Scout agent returns weather snapshots, inspiration bullet points, and recommended themes. Supervisor merges with flights.
5. Supervisor responds to proxy; proxy streams back to UI.

### Location Detection

- UI already provides `lat`/`lon`.
- Supervisor calls a public IATA service (e.g., [AviationStack](https://aviationstack.com/) `/airports` endpoint) via Strands `http_request`, filters for Lufthansa Group coverage, and selects the closest candidate based on coordinates.
- The detected airport is confirmed with the user before locking it as default (`sessionAttributes.default_origin`).

### AWS Strands Constructs

- **Flows**: single Strands project `inspiria-supervisor` (deployed in the AWS account/profile `dAisy_picker`):
  - Node 1: `ingest_user_input`.
  - Node 2: `normalize_time_location` (tool call fan-out).
  - Node 3: `decide_agent` (policy referencing guardrails + heuristics).
  - Nodes 4–5: agent invocations (Flight Search or Destination Scout).
  - Node 6: `compose_response`.
- **State**: Use Strands memory store to persist:
  - persona (`paul|gina|bianca`),
  - `default_origin`,
  - latest antiPhaser snapshot (already emitted by Lambda),
  - conversation summary for Destination Scout context.

The initial manifest lives in `config/supervisor.strands.json` and encodes these nodes, personas, and routing thresholds.

## Suggested Repo Structure

```
strands/
  README.md
  docs/
    ARCHITECTURE.md
    IMPLEMENTATION_PLAN.md
  supervisor/
    package.json
    src/
      handler.ts         # Strands Supervisor Lambda
      policies/...
  agents/
    flight_search/
      README.md
      handler.py        # wraps existing aws/lambda_function helpers
    destination_scout/
      README.md
      handler.ts        # Node-based scout agent
  config/
    supervisor.strands.json
    flight_search.strands.json
    destination_scout.strands.json
```

Until we split this folder into a new repo, we keep the code colocated but deploy via separate CI pipelines.

## Tooling & Integrations

- **Google Flights / Calendar / Explore**: reuse `google-api.mjs` (Render) – no change required; just expose the base URL to the agents.
- **Weather**: Open-Meteo (free) + fallback to Tomorrow.io if we need higher fidelity.
- **Destination Knowledge**: SearchAPI’s `google_travel_explore`, Wikipedia summary API, Lufthansa editorial CMS (future).
- **Time Phrase Parsing**: handled inside the Supervisor model (Claude 3.5 Sonnet) plus the Strands `current_time` tool for temporal grounding—no antiPhaser dependency.
- **IATA Lookup**: AviationStack (or similar public REST API) accessed through Strands `http_request`, cached per session.
- **Guardrails**: Apply existing `daisy_guardrails.json` plus new persona-specific guardrails when we stand up the Strands project.

## Implementation Milestones

1. **Bootstrap repo**
   - Copy this `strands` folder into a new Git repo.
   - Wire up shared ESLint/prettier + Ruff (Python) configs.
2. **Supervisor Lambda**
   - TypeScript handler with AWS Lambda Powertools (Tracing + Idempotency).
   - Strands manifest referencing Bedrock Claude Sonnet.
   - Integrate IATA lookup + antiPhaser toolcalls.
3. **Flight Search agent Lambda**
   - Extract flight helpers from `aws/lambda_function.py` into a pip-installable module.
   - Provide GET/POST wrappers for Google APIs.
4. **Destination Scout agent**
   - Node.js 20 Lambda hitting SearchAPI + Open-Meteo.
   - Return structured JSON ready for Supervisor summarisation.
5. **UI & Proxy integration**
   - Add new `/invoke-strands` endpoint in `proxy.mjs`.
   - Feature flag in each frontend to route to Strands supervisor.
6. **End-to-end tests**
   - Jest tests for orchestrator logic (mock Strands events).
   - Playwright smoke tests for Bianca/Gina/Paul hitting the Strands path.

## Open Questions

- Persona tuning is required: Supervisor responses must follow the Paula, Gina, and Bianca blueprints stored in `docs/paula.md`, `docs/gina.md`, and `docs/bianca.md`.
- Destination Scout relies exclusively on SearchAPI’s `google_travel_explore`; no other flight/event APIs are planned for this phase.
- How do we mirror Strands state into analytics? Plan: emit CloudWatch logs + push transcripts to the existing `s3escalator`.

This document will evolve as we implement each milestone.
