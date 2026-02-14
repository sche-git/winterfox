# Frontend Migration + Storyline TODO

## 1) Backend/API Contract Stabilization
- [x] Fix config API to expose `lead_agent` and remove stale `agent.role` assumption.
- [x] Fix report generation API to use Lead agent config.
- [x] Expose split cycle costs (`lead_llm_cost_usd`, `research_agents_cost_usd`) in cycle list/detail.
- [x] Expose direction-oriented fields in cycle detail (`directions_*`, `consensus_directions`) while keeping legacy fields for compatibility.
- [x] Expose split cost stats and direction count in overview stats.

## 2) Frontend Data Model Migration
- [x] Update TypeScript API types for direction-first model and split costs.
- [x] Keep temporary compatibility aliases for legacy fields to avoid breaking existing views.
- [x] Update cycle store consumers to prefer direction terminology.

## 3) Graph + Overview + Report Reframe
- [x] Remove hard dependency on old node type taxonomy from Graph views.
- [x] Reframe Overview metrics for direction-first model.
- [ ] Improve Report page status states and metadata display for fresh/stale context.

## 4) Storyline Experience (History Page)
- [x] Replace left-list + detail sheet layout with vertical storyline feed.
- [ ] Design cycle “bubble” cards with key narrative data:
  - [x] target direction
  - [x] lead reasoning summary
  - [x] direction delta (+created, ~updated)
  - [x] split cost chips
  - [x] expand for synthesis + agent highlights + searches
- [x] Add lightweight animations (staggered entrance, smooth expand/collapse).
- [x] Add filters/toggles (`All`, `High Impact`, `High Cost`, `Failures`).

## 5) Verification
- [x] Run frontend build and fix compile/type errors.
- [ ] Run targeted backend tests for API/report paths.
- [ ] Manually validate end-to-end dashboard flow with recent cycle data.
