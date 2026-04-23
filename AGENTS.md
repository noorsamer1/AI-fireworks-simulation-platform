# AGENTS.md

> Compact, agent-IDE-friendly handoff. Full spec lives in `PYROMIND_AGENT_BUILD_SPEC.md` — read that first. This file is a fast-lookup reference during execution, not a replacement.

## Project in one paragraph

PyroMind is a cross-platform desktop app (Tauri + React + Python sidecar) that turns any song into a fully choreographed, physics-simulated fireworks show via a LangGraph pipeline of 9 specialized agents. Local-first (Ollama + Qwen 2.5 32B), offline-capable, deterministic where possible, with a human-in-the-loop at every stage. Exports to FireOne CSV and a Finale 3D-compatible subset.

## Rules the agent must never break

1. **Do not scrape, bundle, or redistribute** Finale 3D supplier catalogs, proprietary VDL definitions, or any manufacturer's effect descriptions without explicit written permission. Only ingest catalogs the user uploads themselves or that a manufacturer has signed a partnership agreement for (tracked in `data/partnerships.yaml`).
2. **Local model first.** Cloud LLMs (Claude, OpenAI, OpenRouter) are opt-in fallbacks, never defaults.
3. **Safety rules are code, not prompts.** Never ask an LLM to judge whether a firing configuration is safe.
4. **Every agent output is a validated Pydantic model.** No free-form strings cross agent boundaries.
5. **Every phase has a gate.** Do not start the next phase until the gate is green.
6. **All strings through i18n from day one.** English + Arabic, RTL-correct.
7. **No feature creep.** Out-of-spec changes go in `docs/proposals/` and wait for approval.

## The 9 agents (one line each)

| # | Agent | Reads | Writes | Model |
|---|---|---|---|---|
| 1 | `Orchestrator` | user request | routes graph | none |
| 2 | `AudioAnalyst` | song file | `audio` | Demucs + madmom + MERT + CLAP |
| 3 | `ShowDirector` | `audio` + constraints | `plan` | Qwen 32B / Claude 4.5 |
| 4 | `EffectLibrarian` | `plan` | `candidates` | bge-m3 + rules |
| 5 | `Choreographer` | `audio` + `plan` + `candidates` | `choreography` | Qwen 32B / Claude 4.5 |
| 6 | `EffectCaster` | `choreography` | `firing_script` | none (pure logic) |
| 7 | `SafetyAuditor` | `firing_script` | `safety` | none (codified rules) |
| 8 | `Simulator` | `firing_script` | `simulation` | custom physics |
| 9 | `Exporter` | full state | files on disk | none |
| + | `Critic` | full state | `critique` | Claude 4.5 / Qwen 32B |

## Tech stack — one-line-each

- **Shell:** Tauri 2.x (Rust). Fallback: Electron if Rust blocks >1 day.
- **Frontend:** React 18 + TS + Vite + Tailwind + Zustand + shadcn/ui + React Three Fiber + Rapier.
- **Backend:** Python 3.11 + FastAPI + uvicorn as Tauri sidecar, LangGraph for agents.
- **LLM local:** Ollama → `qwen2.5:32b-instruct-q5_K_M`. Premium: `llama3.3:70b`.
- **LLM cloud:** Claude Sonnet 4.5 via Anthropic API or OpenRouter.
- **Audio:** Demucs v4, librosa 0.10+, madmom 0.16+, essentia 2.1+, MERT-v1-330M, CLAP (LAION).
- **Storage:** SQLite + sqlite-vec.
- **Embeddings:** bge-m3 (multilingual, 1024-dim).
- **Packaging:** Tauri's built-in `tauri build` → signed `.msi` + `.dmg`.

## Phase gates — cheat sheet

- **P0 Inventory + skeleton:** window shows "Sidecar OK", CI green on empty project. (1d)
- **P1 Data layer:** catalog queryable via REST. (2d)
- **P2 AudioAnalyst:** 5 fixture songs match golden JSON within tolerance. (3d)
- **P3 Graph + orchestrator:** stub graph end-to-end, WS events reach UI. (2d)
- **P4 ShowDirector + EffectLibrarian:** plan section-energy Pearson > 0.5; retrieval P@10 > 0.7. (3d)
- **P5 Choreographer + EffectCaster + SafetyAuditor:** timing within 20ms of onsets; 15 safety checks each with a dedicated test. (4d)
- **P6 Simulator + timeline UI:** show plays synced to audio ±10ms. (4d)
- **P7 Exporter + Critic + chat revisions:** round-trip FireOne CSV; revision requests re-run only downstream agents. (2d)
- **P8 Polish + i18n + packaging:** signed Win + Mac installers; 15-min-to-first-show UX test passes. (3d)

## First five commands

```bash
# 1. Clone and inventory
git clone https://github.com/noorsamer1/AI-fireworks-simulation-platform pyromind
cd pyromind
tree -L 3 -I 'node_modules|__pycache__|.venv' > docs/legacy_inventory.md

# 2. Freeze legacy
mkdir -p legacy/2026-04-23-original
git mv backend frontend data scripts legacy/2026-04-23-original/ 2>/dev/null || true

# 3. New skeleton
pnpm create tauri-app@latest pyromind-app --template react-ts --manager pnpm
# (or Electron fallback — see ADR-001)

# 4. Python sidecar bootstrap
cd pyromind-app && mkdir -p src-python && cd src-python
uv init --python 3.11 && uv add fastapi uvicorn pydantic langgraph ollama

# 5. Health check wiring — write src-tauri/src/sidecar.rs spawning the sidecar
#    + src/lib/api.ts polling /health + render "Sidecar OK" in App.tsx
```

## Where to look when stuck

- **Library API unclear?** `python -c "import X; help(X.thing)"` or read `node_modules/X/dist/index.d.ts`. Never guess.
- **Design decision unclear?** Write `docs/proposals/NNN-question.md` and stop.
- **Spec contradicts reality?** Write `docs/decisions/ADR-NNN.md` documenting the divergence, then continue.

## Done criteria (v1.0)

Drop song in → ≤10 min → 3D show playing synced to audio → exports to FireOne CSV → imports into our own CSV parser round-trip → works offline → EN + AR UI → signed installers exist.

---
*If in doubt, re-read `PYROMIND_AGENT_BUILD_SPEC.md`. This file is a shortcut, not a replacement.*
