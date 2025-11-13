# Implementation Plan – Lufthansa Inspiria (AWS Strands)

## Phase 0 – Repo Bootstrap (This PR)

- [x] Document architecture, agent charters, and toolchain requirements.
- [ ] Spin off `strands/` into a dedicated repo (e.g., `lufthansa-inspiria-strands`).
- [ ] Configure linting/formatting: ESLint + Prettier for TS, Ruff + Black for Python.
- [ ] Set up CI skeleton (GitHub Actions) for lint/test/deploy.

## Phase 1 – Supervisor Foundation

| Task | Owner | Notes |
|------|-------|-------|
| Create `supervisor` Lambda (TypeScript) | TBD | Handles Strands entry point + orchestrator logic |
| Define Strands manifest (`config/supervisor.strands.json`) | TBD | Includes nodes, policies, guardrails |
| Implement time/location normalisation | TBD | Uses Strands `current_time` tool + external public IATA API via `http_request` |
| Session memory + persona routing | TBD | Use Strands memory store; map to UI persona |

**Models:** use Bedrock Claude 3.5 Sonnet for reasoning, fallback to Amazon Nova for resilience.

## Phase 2 – Flight Search Agent

- Extract shared helpers from `aws/lambda_function.py` into `strands/shared/flight_utils`.
- Create Python 3.12 Lambda (`agents/flight_search/handler.py`) that:
  - Accepts a normalised itinerary payload.
  - Calls Google Flights/Calendar/Explore via existing Render microservice.
  - Returns itineraries + price calendar + alternatives.
- Provide lightweight natural-language wrapping (Llama 3.1 70B Instruct) only if we need textual explanations; otherwise return JSON for Supervisor to narrate.

## Phase 3 – Destination Scout Agent

- Node.js 20 Lambda with:
  - SerpAPI Google Travel Explore search.
  - Open-Meteo weather snapshot for near-term dates.
  - Optional Wikipedia summary fallback.
- Add caching + throttling (½-second delay between SerpAPI calls).
- Return inspiration cards: `{destination, whyNow, weather, events, sources}`.

## Phase 4 – Strands Orchestration + Tooling

- Compose Strands project (in profile `dAisy_picker`) linking Supervisor + both agents.
- Encode routing rules:
  - If itinerary completeness score ≥ 0.7 ⇒ Flight Search.
  - Else, Destination Scout first, then ask clarifying questions.
- Provide guardrail instructions per persona (Paul/Gina/Bianca).
- Add evaluator tests (Strands replay) for regression coverage.

## Phase 5 – UI / Proxy Integration

- Add `/invoke-strands` path to `proxy.mjs` (toggle via env `USE_STRANDS=true`).
- Frontends (Paul/Gina/Bianca):
  - Add “engine selector” for Classic vs. Strands.
  - Ensure lat/lon is passed consistently to supervisor.
- End-to-end smoke tests (Playwright) hitting Render staging.

## Phase 6 – Observability + Launch

- CloudWatch dashboards for each Lambda + Strands metrics.
- Integrate with `s3escalator` for transcript storage.
- Roll out gradually: Gina → Paul → Bianca.
- Post-launch: collect analytics to tune routing thresholds.

---

**Dependencies:** SerpAPI key, Open-Meteo (no key), Bedrock model access (Claude, Llama, Nova), AWS Strands GA access.

**Risks/Mitigations:**
- Strands availability – keep the existing Bedrock Agent path as fallback.
- SerpAPI quota – add caching + degrade gracefully to Explore data we already store.
- UI drift – reuse existing personas to avoid rebranding effort.
