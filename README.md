# Lufthansa Inspiria (AWS Strands)

Multi-agent orchestration for Lufthansa Group inspiration assistants, powered by **AWS Strands** (target AWS profile: `dAisy_picker`). This repository (currently a sub-folder until we split it into its own repo) contains the system design, agent specifications, and deployment plan for a trio of cooperating agents:

1. **Supervisor (Conductor)** – Reasoning + orchestration layer. Converts time phrases, builds the Strands conversation graph, tracks session context, delegates to sub-agents, and produces the final response.
2. **Flight Search Agent** – Talks to the Google Flights/Calendar/Explore microservices exposed in this repo (`google-api.mjs`). Supports one-way and round-trip itineraries.
3. **Destination Scout Agent** – Fetches inspirational destination intel (city highlights, weather, events). Starts with search APIs (SerpAPI, Open-Meteo) and can extend to Bedrock RAG or internal travel CMS feeds.

The existing **Paul/Gina/Bianca** React frontends remain the user entry point; their proxy just needs a new `/invoke` target that calls the AWS Strands supervisor. The Browser UI already passes `lat/lon`, which enables auto-detection of the nearest Lufthansa Group airport (confirmed by the Supervisor before proceeding) via a public IATA lookup API (no internal `tools/iata/lookup` usage).

## Current Status

- ✅ Architecture + agent specs captured in `docs/ARCHITECTURE.md`.
- ✅ Initial Strands workflow sketch with tool wiring and Bedrock model recommendations.
- 🔜 Build the Strands manifest (`strands/config/supervisor.strands.json`) and lambdas.
- 🔜 Mirror this folder into a dedicated repo (e.g., `github.com/LHGroup/strands-inspiria`).

## Running Plan

1. Implement Supervisor Lambda using Bedrock **Claude 3.5 Sonnet** (reasoning) + **Nova Lite** for summarisation, backed by AWS Strands conversation state. It uses the Strands `current_time` tool (instead of antiPhaser) plus an external IATA API accessible through Strands `http_request`.
2. Wrap Flight Search agent as its own Lambda that reuses `aws/lambda_function.py` logic (or splits the flight-specific helpers into a shared package).
3. Build Destination Scout agent (Node.js or Python) calling SerpAPI + Open-Meteo, returning structured JSON.
4. Deploy all three as Strands agents, define the orchestration policies, then point the existing proxy (`proxy.mjs`) to the Supervisor invoke endpoint.

See the docs for the detailed breakdown.

> **Persona Note**: The Supervisor will support three persona-flavoured response styles (Paul, Gina, Bianca, or new variants). Final instructions for each persona/version will be incorporated once provided.
