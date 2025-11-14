# Lufthansa Inspiria (AWS Strands)

Multi-agent orchestration for Lufthansa Group inspiration assistants, powered by **AWS Strands** (target AWS profile: `dAisy_picker`). This repository (currently a sub-folder until we split it into its own repo) contains the system design, agent specifications, and deployment plan for a trio of cooperating agents:

1. **Supervisor (Conductor)** – Reasoning + orchestration layer. Converts time phrases, builds the Strands conversation graph, tracks session context, delegates to sub-agents, and produces the final response (`supervisor/agent.py`).
2. **Flight Search Agent** – Talks to Google Flights via SearchAPI using the Strands `http_request` tool (`flight_search/agent.py`). Supports one-way and round-trip itineraries.
3. **Destination Scout Agent** – Fetches inspirational destination intel (city highlights, weather, events). Leans on SearchAPI (Google Travel Explore), Open-Meteo, and can extend to Bedrock RAG or internal travel CMS feeds.

The existing **Paul/Gina/Bianca** React frontends remain the user entry point; their proxy just needs a new `/invoke` target that calls the AWS Strands supervisor. The Browser UI already passes `lat/lon`, which enables auto-detection of the nearest Lufthansa Group airport (confirmed by the Supervisor before proceeding) via a public IATA lookup API (no internal `tools/iata/lookup` usage).

## Current Status

- ✅ Architecture + agent specs captured in `docs/ARCHITECTURE.md`.
- ✅ Initial Strands workflow sketch with tool wiring and Bedrock model recommendations.
- ✅ Destination Scout agent prompt, SearchAPI/Open-Meteo service + Lambda handler (`destination_scout/agent.py`, `destination_scout/service.py`, `destination_scout/handler.py`).
- ✅ Draft Strands manifest describing supervisor routing (`config/supervisor.strands.json`).
- ✅ Flight Search service + Lambda handler powered by SearchAPI Google Flights/Calendar (`flight_search/service.py`, `flight_search/handler.py`).
- ✅ Supervisor renderers + prompts wired to `conversation_state.destination_cards` and `flight_results`.
- 🔜 Validate the Strands manifest via the Strands CLI and hook it into the deployment Lambdas.
- 🔜 Mirror this folder into a dedicated repo (e.g., `github.com/LHGroup/strands-inspiria`).

## Running Plan

1. Implement Supervisor Lambda using Bedrock **Claude 3.5 Sonnet** (reasoning) + **Nova Lite** for summarisation, backed by AWS Strands conversation state. It uses the Strands `current_time` tool (instead of antiPhaser) plus an external IATA API accessible through Strands `http_request`.
2. Wrap Flight Search agent as its own Lambda that reuses `aws/lambda_function.py` logic (or splits the flight-specific helpers into a shared package).
3. Build Destination Scout agent (Node.js or Python) calling SearchAPI + Open-Meteo, returning structured JSON.
4. Deploy all three as Strands agents, define the orchestration policies, then point the existing proxy (`proxy.mjs`) to the Supervisor invoke endpoint.

See the docs for the detailed breakdown. To run locally, copy `.env.example` to `.env` and set `SEARCHAPI_KEY` (used for Google Travel Explore, Flights, and Flights Calendar). Persona guardrails for Paula, Gina, and Bianca live in `docs/paula.md`, `docs/gina.md`, and `docs/bianca.md`.

> **Persona Note**: The Supervisor will support three persona-flavoured response styles (Paul, Gina, Bianca, or new variants). Final instructions for each persona/version will be incorporated once provided.

## Setup
```bash
cp .env.example .env
# populate SEARCHAPI_KEY
```

```bash
pip install -r requirements.txt
```

For contributor tooling (Ruff, Black, pytest), install the dev extras:

```bash
pip install -r requirements-dev.txt
# or
pip install -e .[dev]
```

## Destination Scout Service

- Lambda entry point: `destination_scout/handler.lambda_handler`.
- Request contract: `DestinationScoutRequest` (see `destination_scout/service.py`) — expects a normalised `time_window`, `departure_id`, optional `arrival_ids` or `interests`, and returns structured destination cards.
- External calls: `https://www.searchapi.io/api/v1/search?engine=google_travel_explore` (Authorization header from `SEARCHAPI_KEY`) plus Open-Meteo daily snapshots.
- Built-in safeguards: in-memory cache (16 entries) and a 0.5 s pacing delay between SearchAPI calls to stay within quota.
- The Supervisor consumes the cards via `conversation_state.destination_cards` (see `config/supervisor.strands.json`).
- Local dry-run: `python scripts/run_destination_scout.py payload.json` (omit the argument to use the built-in sample payload).

## Flight Search Service

- Lambda entry point: `flight_search/handler.lambda_handler`.
- Request contract: `FlightSearchRequest` (see `flight_search/service.py`) — expects `departure_id`, `arrival_id`, ISO `outbound_date`, optional `return_date`, traveller counts, cabin, plus optional `calendar_window` for monthly grids.
- External calls: `https://www.searchapi.io/api/v1/search?engine=google_flights` (mandatory) and `engine=google_flights_calendar` when a window is provided.
- Response bundle: raw SearchAPI payloads for flights and calendar plus metadata with the Google URLs.
- Local dry-run: `python scripts/run_flight_search.py payload.json` (omit the argument to use the built-in sample payload).

## Supervisor Renderers

- Functions in `supervisor/renderers.py` convert `conversation_state.destination_cards` and `conversation_state.flight_results` into narrative-ready snippets (used by Paula/Gina/Bianca).
- Reusable airline/price helpers live in `shared/flight_utils.py` and back both agents + supervisor formatting.
- `supervisor/composer.py` exposes `compose_reply`, which stitches persona openers/closers with the rendered destination + flight sections for final replies or tooling-based tests.
- Gina’s questionnaire is enforced in `compose_reply` so she always repeats the mandatory “choose 1–4” prompt until `conversation_state.travel_personality_choice` is set; the prompt now instructs the supervisor to write that value as soon as the traveler answers.
- Flight summaries are rendered in the multi-line format shown in the spec (Direct Flights/Connecting Flights, aircraft, amenities, baggage, price) with up to 10 itineraries surfaced and Star Alliance fallbacks handled automatically when Lufthansa Group flights are unavailable.

## Local CLI Chat

Need to send ad-hoc prompts without crafting JSON payloads? Copy `.env.example` to `.env`, set `SEARCHAPI_KEY`, and run:

```bash
# Supervisor persona chat (sub-agents stay hidden)
python scripts/chat_agent.py --persona paula
```

The script mirrors Strands’ personal-assistant samples: it toggles `STRANDS_TOOL_CONSOLE_MODE`, keeps session state in memory, and streams responses from the supervisor while it quietly delegates to Flight Search or Destination Scout tools.
