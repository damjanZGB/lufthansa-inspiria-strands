# Implementation Plan – Lufthansa Inspiria (AWS Strands)

## Phase 0 – Repo Bootstrap (This PR)

- [x] Document architecture, agent charters, and toolchain requirements.
- [ ] Spin off this folder into its own repo (still hosted inside the legacy mono-repo).
- [x] Configure linting/formatting for Python (Ruff + Black in `pyproject.toml`).  
        *TODO when TypeScript UI code moves here: ESLint + Prettier.*
- [x] Set up CI skeleton (GitHub Actions `ci.yml` runs Ruff/Black/pytest on PRs).

## Phase 1 – Supervisor Foundation

| Task | Owner | Notes |
|------|-------|-------|
| Create Supervisor runtime | ✅ | Python Strands agent factory + CLI harness exist; Lambda packaging pending. |
| Define Strands manifest (`config/supervisor.strands.json`) | ✅ | Draft committed with routing + persona guardrails. |
| Implement time/location normalisation | 🟡 | `current_time` + public IATA lookup wired into tools; need explicit persistence of persona questionnaire answers. |
| Session memory + persona routing | 🟡 | Persona instructions loaded; Gina questionnaire enforced in composer, but conversation_state writes still required. |

**Models:** running on Bedrock Claude 3 Haiku by default (configurable). Need to test inference profile flow for Sonnet 3.5.

## Phase 2 – Flight Search Agent

- [x] Extract shared helpers into `shared/flight_utils` (pricing, Star Alliance fallbacks).
- [x] Create Python 3.12 Lambda (`flight_search/handler.py`) that:
  - Accepts a normalised itinerary payload.
  - Calls SearchAPI Google Flights + Flights Calendar.
  - Returns itineraries + price calendar + alternatives.
- [x] Enforce Lufthansa → Star Alliance fallback with up to 10 itineraries, surface scope in metadata.
- [ ] Provide light NL summarisation only if downstream tooling requires it (currently supervisor handles copy).

## Phase 3 – Destination Scout Agent

- [x] Python Strands agent factory and prompt scaffolding (`destination_scout/agent.py`).
- [x] Python Lambda/service that calls SearchAPI `google_travel_explore` plus Open-Meteo to build structured cards (add caching + ½-second pacing between SearchAPI calls).
- Return inspiration cards: `{destination, whyNow, weather, events, sources}`.

## Phase 4 – Strands Orchestration + Tooling

- [ ] Compose Strands project (AWS profile `dAisy_picker`) linking Supervisor + both agents.
- [ ] Encode routing rules:
  - If itinerary completeness score ≥ 0.7 ⇒ Flight Search.
  - Else, Destination Scout first, then ask clarifying questions.
- [x] Provide guardrail instructions per persona (docs + prompt block).
- [ ] Add evaluator tests (Strands replay) for regression coverage once manifests are validated.
- [x] CLI harness (`scripts/chat_agent.py`) for local debugging; add persona persistence + weather summary enforcement (done).

## Phase 5 – UI / Proxy Integration

- [ ] Add `/invoke-strands` path to `proxy.mjs` (toggle via env `USE_STRANDS=true`).
- [ ] Frontends (Paul/Gina/Bianca):
  - Add “engine selector” for Classic vs. Strands.
  - Ensure lat/lon and persona choice are passed consistently to supervisor.
- [ ] End-to-end smoke tests (Playwright) hitting Render staging.

## Phase 6 – Observability + Launch

- [ ] CloudWatch dashboards for each Lambda + Strands metrics.
- [ ] Integrate with `s3escalator` for transcript storage.
- [ ] Roll out gradually: Gina → Paul → Bianca.
- [ ] Post-launch: collect analytics to tune routing thresholds, monitor SearchAPI quota fallback usage, and ensure destination weather summary accuracy.

---

**Dependencies:** SearchAPI key, Open-Meteo (no key), Bedrock model access (Claude, Llama, Nova), AWS Strands GA access.

**Risks/Mitigations:**
- Strands availability – keep the existing Bedrock Agent path as fallback.
- SearchAPI quota – add caching + degrade gracefully to Explore data we already store.
- UI drift – reuse existing personas to avoid rebranding effort.
- Bedrock inference changes – Sonnet 3.5 requires inference profiles; keep Haiku fallback until profiles are provisioned.
