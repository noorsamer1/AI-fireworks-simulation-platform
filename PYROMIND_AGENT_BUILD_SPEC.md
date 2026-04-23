# PyroMind AI — Full Agent-Mode Build Specification

> **Audience:** An autonomous coding agent (Claude Code, Cursor agent, Cline, etc.)
> **Goal:** Take the repo `noorsamer1/AI-fireworks-simulation-platform` (Python backend, React frontend, ~9 months old) and evolve it into a production-grade **desktop application** that turns any WAV/MP3/FLAC song into a fully choreographed, physically simulated fireworks show — end to end, no human in the loop required, but with optional human-in-the-loop refinement at every stage.
> **Author:** Noor Samer (PyroMind project owner)
> **Target delivery:** A runnable, installable desktop app (Windows + macOS) + the agent pipeline that powers it.

---

## 0. How to use this document

This document is both a **spec** and a **master prompt**. Feed it to a coding agent with agent-mode enabled and instruct:

> *"Read `PYROMIND_AGENT_BUILD_SPEC.md` in full. Build the project exactly as specified, section by section, in the order given. Implement every agent, every contract, every test. After each Phase (0 through 8), stop, self-test against the acceptance criteria for that phase, and produce a short progress report before starting the next phase. Do not skip phases. Do not invent features outside this spec without first proposing them and waiting for approval."*

The agent should treat Sections 1–3 as context, Sections 4–6 as architecture, Section 7 as the agent contracts (most important), and Sections 8–11 as the execution plan.

---

## 1. Why this project exists

Professional fireworks choreography software (Finale 3D, FireOne, Pyrodigital, Showsim) costs $3,000–$15,000 per seat, is Windows-only, requires a manual click-to-place workflow, and has essentially zero AI. A display that should take 2 hours of creative work takes pyrotechnicians 20–40 hours of mouse clicks.

**PyroMind's thesis:** a coordinated team of specialized AI agents, fed a song and a few constraints, can produce a firing script that matches or exceeds what a mid-level human designer produces in 40 hours — in under 10 minutes.

The output is a **simulated** show (real-time 3D preview) plus an **exportable firing script** in the industry-standard `.fdb`-compatible JSON / FireOne CSV / Finale 3D `.f3d` format that a licensed pyrotechnician can load into actual firing hardware.

---

## 2. Existing repo — what's there, what to keep, what to throw away

Based on the 9-month-old repo (`backend/`, `frontend/`, `data/`, `scripts/`, Python 84% / JS 15.8%):

**Keep and extend:**
- Any existing React canvas code for rendering fireworks → evolve into the 3D simulation view.
- Any Python audio analysis code (likely librosa-based) → becomes one input to the `AudioAnalyst` agent, not the whole thing.
- Any effect catalog/dataset in `data/` → this is gold; it feeds the `EffectLibrarian` agent.
- The scraping scripts → the `DatasetScraper` agent consumes and extends these.

**Replace:**
- The web-only deployment model → desktop (Tauri + React + Python sidecar).
- Any monolithic "generate show" function → decomposed into the 9 agents defined in Section 7.
- Any hardcoded effect rules → replaced by LLM-driven semantic retrieval over the effect catalog.

**Don't touch yet (Phase-later):**
- The cafe POS, BMW, or anything unrelated — this project is PyroMind only.

**Agent's first task:** clone the repo, run `tree -L 3 -I 'node_modules|__pycache__|.venv'`, read every top-level file, and produce a written inventory (`docs/legacy_inventory.md`) before writing any new code. Do not delete anything from the old code — move it into `legacy/` with a dated subfolder.

---

## 3. Non-negotiable principles

These are hard constraints. Every PR must pass them.

1. **Local-first.** Every model that *can* run locally *must* have a local path. Cloud (OpenRouter / Claude API / OpenAI) is a fallback, never the default. User toggles it in settings.
2. **Offline-capable.** After first-run model download, the entire pipeline must work with no internet.
3. **Deterministic where possible.** Audio analysis, physics simulation, and effect retrieval must be reproducible given the same seed. Only the LLM choreographer step is allowed to be stochastic, and it must log its seed + temperature.
4. **Human-in-the-loop at every stage.** Every agent's output is inspectable, editable, and re-runnable from that point. No "magic black box."
5. **Industry-compatible export.** Output must be importable into at least one real pyro software (FireOne CSV is the easiest target; Finale 3D `.fdb` is the stretch goal).
6. **Safety-first defaults.** No effect below a configurable minimum safety distance. No effect above the configured firing site ceiling. Hard refuse illegal configurations with a clear error — never silently clamp.
7. **GitHub-ready code.** Type hints, docstrings, `ruff` + `black` + `mypy --strict`, 80%+ test coverage on pure-logic modules, CI green.
8. **Arabic/English UI.** Every string goes through i18n from day one. RTL layout tested.
9. **No feature creep without written justification.** If the agent wants to add something not in this spec, it proposes in `docs/proposals/NNN-name.md` and waits.

---

## 4. Target stack

| Layer | Choice | Why |
|---|---|---|
| Desktop shell | **Tauri 2.x** (Rust) | 10 MB vs Electron's 150 MB, native performance, better security model. Fallback: Electron if Rust toolchain blocks progress for >1 day. |
| Frontend | **React 18 + TypeScript + Vite + Tailwind + Zustand + shadcn/ui** | Noor's existing React code carries over; Zustand is simpler than Redux for this scope. |
| 3D rendering | **Three.js + React Three Fiber + drei** | Industry standard for web 3D; physics via `@react-three/rapier`. |
| Audio playback | **Howler.js** in frontend, **pydub + soundfile** in backend | Howler for synced preview, soundfile for analysis. |
| Backend language | **Python 3.11+** | Noor's primary language, all audio/ML libraries are Python. |
| Backend framework | **FastAPI** + **uvicorn** running as a **Tauri sidecar** | Process spawned by Tauri, speaks over localhost + WebSocket for streaming agent progress. |
| Agent orchestration | **LangGraph** (Python) | Graph-based, supports checkpoints, human-in-the-loop interrupts, state persistence. Alternatives rejected: raw LangChain (too brittle), CrewAI (less control over state). |
| LLM (local) | **Ollama** running `qwen2.5:32b-instruct-q5_K_M` as default, `llama3.3:70b` as premium | Qwen 2.5 is the best local choice under 48 GB VRAM as of early 2026; strong structured output, strong Arabic. |
| LLM (cloud fallback) | **Claude Sonnet 4.5** via Anthropic API or OpenRouter | Best-in-class at long structured JSON outputs. |
| Audio source separation | **Demucs v4** (htdemucs) | State of the art, runs on CPU (slow) or CUDA/MPS. |
| Audio feature extraction | **librosa 0.10+**, **madmom 0.16+**, **essentia 2.1+** | Standard stack; madmom for downbeats is non-negotiable. |
| Music semantic embeddings | **MERT-v1-330M** (music-specific) primary, **CLAP (LAION)** as cross-modal bridge | MERT understands musical structure; CLAP lets you retrieve effects by text description. |
| Vector DB | **sqlite-vec** (embedded) | Zero-setup, runs inside the Python sidecar, perfect for local desktop. |
| Embedding model for effects | **bge-m3** via `sentence-transformers` | Multilingual (for Arabic effect descriptions), 1024-dim, fast. |
| Physics / simulation | Custom Three.js particle system + Rapier for debris; **no real external physics lib** | Fireworks don't need FEM-grade accuracy; visual fidelity is the target. |
| Effect catalog storage | SQLite + JSON blobs for complex fields | Ships with the app; updatable from WikiFireworks scrape. |
| Packaging | Tauri's built-in `tauri build` → `.msi` (Win) + `.dmg` (mac) | One command, signed installers. |
| Testing | `pytest` (backend), `vitest` + `playwright` (frontend), custom golden-file tests for agent outputs | Golden files are critical for agent regression testing. |

**If Tauri + Rust becomes a blocker for >1 full day, the agent is authorized to switch to Electron + Python sidecar and note it in `docs/decisions/ADR-001-shell.md`.**

---

## 5. High-level architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    TAURI DESKTOP SHELL (Rust)                    │
│  • Window management   • File I/O   • System tray   • Updater    │
└────────┬────────────────────────────────────────────────┬────────┘
         │ IPC (Tauri commands)                            │ spawns
         ▼                                                  ▼
┌────────────────────────┐                      ┌─────────────────────────┐
│  REACT + R3F FRONTEND  │◄──── WebSocket ─────►│  PYTHON SIDECAR         │
│  • Project workspace   │     (agent events)   │  (FastAPI + LangGraph)  │
│  • 3D simulation view  │                      │  • 9 Agents             │
│  • Timeline editor     │◄──── REST ──────────►│  • Effect DB (SQLite)   │
│  • Agent chat panel    │                      │  • Vector DB            │
│  • Export wizard       │                      │  • Model cache          │
└────────────────────────┘                      └───────┬─────────────────┘
                                                        │
                                                ┌───────▼─────────┐
                                                │ External models │
                                                │ • Ollama        │
                                                │ • Demucs        │
                                                │ • MERT / CLAP   │
                                                │ • Claude API    │
                                                │   (optional)    │
                                                └─────────────────┘
```

### Data flow for "generate show from song"

1. User drops `song.mp3` into the app.
2. `OrchestratorAgent` creates a project, validates the file, and spawns the graph.
3. `AudioAnalyst` → `ShowDirector` → `Choreographer` → `EffectCaster` → `SafetyAuditor` → `Simulator` run in sequence, streaming progress over WebSocket.
4. User reviews the 3D simulation; can chat with `ShowDirector` to request revisions ("more gold, less blue, bigger finale").
5. User exports → `Exporter` produces FireOne CSV + Finale 3D attempt + internal JSON + MP4 render of the simulation.

---

## 6. Project file structure

```
pyromind/
├── README.md
├── LICENSE
├── PYROMIND_AGENT_BUILD_SPEC.md         ← this file, kept in repo
├── .github/workflows/                   ← CI: lint, test, build on all three OSes
├── docs/
│   ├── legacy_inventory.md              ← agent produces in Phase 0
│   ├── architecture.md
│   ├── agents/                          ← one MD per agent, auto-generated from docstrings
│   ├── decisions/                       ← ADRs
│   └── proposals/                       ← out-of-spec change proposals
├── legacy/                              ← old repo contents, frozen
├── src-tauri/                           ← Rust shell
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands.rs                  ← Tauri IPC commands
│   │   └── sidecar.rs                   ← spawns Python, health checks
│   ├── tauri.conf.json
│   └── Cargo.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ProjectWorkspace/
│   │   │   ├── SimulationView/          ← R3F scene
│   │   │   ├── Timeline/                ← DAW-style timeline
│   │   │   ├── AgentChatPanel/
│   │   │   ├── EffectBrowser/
│   │   │   └── ExportWizard/
│   │   ├── stores/                      ← Zustand stores
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   ├── api.ts                   ← REST client to sidecar
│   │   │   ├── ws.ts                    ← WS client for agent events
│   │   │   └── i18n/
│   │   │       ├── en.json
│   │   │       └── ar.json
│   │   └── types/                       ← shared types, auto-gen from backend
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── pyproject.toml
│   ├── pyromind/
│   │   ├── __init__.py
│   │   ├── api/                         ← FastAPI routes
│   │   │   ├── projects.py
│   │   │   ├── agents.py
│   │   │   ├── effects.py
│   │   │   ├── export.py
│   │   │   └── ws.py
│   │   ├── agents/                      ← THE AGENTS (see Section 7)
│   │   │   ├── base.py                  ← BaseAgent + shared types
│   │   │   ├── orchestrator.py
│   │   │   ├── audio_analyst.py
│   │   │   ├── show_director.py
│   │   │   ├── choreographer.py
│   │   │   ├── effect_librarian.py
│   │   │   ├── effect_caster.py
│   │   │   ├── safety_auditor.py
│   │   │   ├── simulator.py
│   │   │   ├── exporter.py
│   │   │   └── critic.py
│   │   ├── graph/                       ← LangGraph wiring
│   │   │   ├── state.py                 ← the shared ShowState TypedDict
│   │   │   ├── build.py                 ← graph construction
│   │   │   └── checkpoints.py
│   │   ├── audio/                       ← pure-Python audio utilities
│   │   │   ├── separation.py            ← Demucs wrapper
│   │   │   ├── features.py              ← librosa / madmom
│   │   │   ├── embeddings.py            ← MERT / CLAP
│   │   │   └── sections.py              ← structural segmentation
│   │   ├── physics/
│   │   │   ├── ballistics.py            ← shell trajectory math
│   │   │   └── effects_model.py         ← burst geometry
│   │   ├── catalog/
│   │   │   ├── db.py                    ← SQLite schema
│   │   │   ├── scraper.py               ← WikiFireworks + others
│   │   │   ├── importer.py              ← Finale 3D / FireOne catalog import
│   │   │   └── vectors.py               ← sqlite-vec integration
│   │   ├── exporters/
│   │   │   ├── fireone_csv.py
│   │   │   ├── finale3d_fdb.py
│   │   │   ├── pyromind_json.py         ← canonical internal format
│   │   │   └── video_render.py
│   │   ├── models/                      ← pydantic models, the wire schemas
│   │   │   ├── show.py
│   │   │   ├── effect.py
│   │   │   ├── audio.py
│   │   │   └── events.py                ← WS event schemas
│   │   ├── i18n/
│   │   └── config.py
│   └── tests/
│       ├── agents/                      ← one test module per agent
│       ├── golden/                      ← reference outputs
│       ├── fixtures/                    ← sample songs (CC0 only!)
│       └── integration/
├── data/
│   ├── seed_catalog.sqlite              ← ~500 curated effects, ships with app
│   ├── seed_catalog.json
│   └── samples/                         ← test songs (CC0)
└── scripts/
    ├── build_all.sh
    ├── update_catalog.py                ← re-runs the scraper
    ├── download_models.py               ← fetches MERT, CLAP, Demucs on first run
    └── gen_types.py                     ← emits TS types from pydantic
```

---

## 7. The Agents — contracts

This is the most important section. Every agent is a **pure function from state to state** inside LangGraph. State is a single TypedDict `ShowState` defined in `backend/pyromind/graph/state.py`.

### 7.0 Shared `ShowState`

```python
from typing import TypedDict, Literal, NotRequired
from pyromind.models.show import Show, AudioAnalysis, ShowPlan, FiringScript, SafetyReport, SimulationArtifact

class ShowState(TypedDict):
    # --- identity ---
    project_id: str
    song_path: str
    user_constraints: "UserConstraints"       # see 7.0.1
    language: Literal["en", "ar"]

    # --- populated by agents ---
    audio: NotRequired[AudioAnalysis]         # by AudioAnalyst
    plan: NotRequired[ShowPlan]               # by ShowDirector
    choreography: NotRequired["Choreography"] # by Choreographer
    firing_script: NotRequired[FiringScript]  # by EffectCaster
    safety: NotRequired[SafetyReport]         # by SafetyAuditor
    simulation: NotRequired[SimulationArtifact] # by Simulator
    critique: NotRequired["Critique"]         # by Critic
    exports: NotRequired[dict[str, str]]      # by Exporter

    # --- control ---
    errors: list[str]
    revision_requests: list[str]              # user messages that re-enter the graph
    seed: int
    trace_id: str
```

**`UserConstraints` (7.0.1):**

```python
class UserConstraints(BaseModel):
    duration_mode: Literal["full_song", "custom"] = "full_song"
    custom_duration_s: float | None = None
    mood_tags: list[str] = []                  # e.g., ["romantic", "epic", "national"]
    color_palette: list[str] | None = None     # hex or named; None = auto
    budget_tier: Literal["demo", "small", "medium", "large", "mega"] = "medium"
    site: "FiringSite"                          # dimensions, safety rings, ceiling
    calibers_allowed: list[int]                # shell sizes in inches, e.g., [2, 3, 4, 5, 6, 8]
    finale_style: Literal["crescendo", "cascade", "wall", "none"] = "crescendo"
    language: Literal["en", "ar"] = "en"
    random_seed: int = 42
```

Every agent below has: **purpose, inputs (ShowState keys it reads), outputs (keys it writes), model used, determinism notes, failure modes, and test fixtures required.**

---

### 7.1 `OrchestratorAgent`

**Purpose:** Owns the LangGraph. Receives user requests, validates inputs, routes between agents, handles revision loops, writes checkpoints. Not an "LLM agent" — it's the conductor.

**Inputs:** Raw user request (song path + constraints).
**Outputs:** Finished `ShowState` or error.
**Model:** None.
**Determinism:** Fully deterministic.
**Failure modes:** Corrupt song file → reject with clear error; model unavailable → fall back to cloud with user confirmation; agent hangs → timeout + retry with backoff (max 3).
**Tests:** Happy path, each failure mode, checkpoint/resume.

**Graph topology it builds:**

```
START → AudioAnalyst → ShowDirector → Choreographer
          │                               │
          │         EffectLibrarian ◄─────┤ (parallel retrieval)
          │                               │
          ▼                               ▼
        Critic ────────────────────► EffectCaster
          ▲                               │
          │                               ▼
          └──────────── SafetyAuditor ◄───┤
                          │               │
                          ▼               ▼
                      Simulator ────► Exporter → END
                          │
                          └─── (human-in-the-loop interrupt here by default)
```

---

### 7.2 `AudioAnalystAgent`

**Purpose:** Turns a raw audio file into a rich, structured analysis.

**Produces `AudioAnalysis`:**

```python
class AudioAnalysis(BaseModel):
    duration_s: float
    sample_rate: int
    tempo_bpm: float
    tempo_curve: list[tuple[float, float]]    # (time_s, local_bpm)
    beats_s: list[float]
    downbeats_s: list[float]
    onsets_s: list[float]
    key: str
    mode: Literal["major", "minor"]
    loudness_curve: list[float]               # 100 Hz sampling
    spectral_centroid_curve: list[float]
    stems: dict[Literal["drums", "bass", "vocals", "other"], str]  # paths to separated WAVs
    sections: list["Section"]                 # structural, below
    mood_vector: list[float]                  # 10-dim, essentia-derived
    mert_embedding: list[float]               # 768-dim per 5s window, flattened with timestamps
    clap_embeddings: list[tuple[float, list[float]]]  # (time_s, 512-dim)

class Section(BaseModel):
    start_s: float
    end_s: float
    label: Literal["intro", "verse", "chorus", "bridge", "drop", "breakdown", "outro", "instrumental"]
    energy: float                             # 0..1
    novelty: float                            # how different from previous section
```

**Pipeline (deterministic given seed):**
1. Load audio with `soundfile`, normalize to -14 LUFS.
2. Demucs separation (cache by file hash).
3. madmom downbeat tracker + librosa beats (ensemble vote).
4. librosa onset detection, per-stem.
5. Essentia for mood/energy/danceability.
6. Structural segmentation via `msaf` or custom MERT-embedding novelty peaks.
7. MERT-v1-330M embeddings in 5s sliding windows.
8. CLAP embeddings every 2s for later semantic retrieval.

**Model:** No LLM. Pure signal processing + neural embeddings.
**Determinism:** Fully deterministic.
**Failure modes:** Corrupt/truncated audio, unsupported codec, CUDA OOM (falls back to CPU + warning), Demucs timeout (uses librosa-only analysis with degraded quality flag).
**Tests:** Golden files for 5 reference songs (CC0 licensed — one each of rock, classical, EDM, Arabic pop, cinematic).

---

### 7.3 `ShowDirectorAgent`

**Purpose:** Reads the audio analysis + user constraints and writes a **high-level narrative plan** for the show. Thinks like a creative director, not a technician. Answers: "what is the story of this show?"

**Produces `ShowPlan`:**

```python
class ShowPlan(BaseModel):
    title: str
    concept: str                              # 2-3 sentences, the "vision"
    arc: list["PlanSection"]                  # maps 1:1 to audio sections
    palette: "Palette"                        # primary/secondary/accent colors with rationale
    motifs: list["Motif"]                     # recurring visual ideas
    finale_concept: str
    budget_distribution: dict[str, float]     # section_id -> fraction (must sum to 1.0)

class PlanSection(BaseModel):
    audio_section_index: int
    intent: str                               # e.g., "slow reveal, single rising effects, hopeful"
    intensity: float                          # 0..1
    density_per_min: int                      # target effects per minute
    dominant_colors: list[str]
    preferred_effect_families: list[str]      # "comet", "mine", "shell_chrysanthemum", etc.
    avoid: list[str]                          # effect families NOT to use

class Motif(BaseModel):
    id: str
    description: str                          # "twin gold comets on every downbeat of the chorus"
    rule: dict                                # machine-readable rule the Choreographer enforces
```

**Model:** Local LLM (Qwen2.5 32B) with cloud fallback (Claude Sonnet 4.5).
**Prompt pattern:** structured output via JSON schema + few-shot examples drawn from a curated set of 10 hand-designed reference plans.
**Determinism:** Stochastic. Logs seed + temperature. Temperature 0.7 by default, 0.3 for "strict" mode.
**Failure modes:** Invalid JSON → one retry with stricter reminder then fail loud. Budget not summing to 1.0 → auto-normalize with warning. Unknown effect family → warning, not error.
**Tests:** Schema validity on 20 varied inputs; coherence check (does the plan's arc match the audio energy curve? measured as Pearson correlation > 0.5).

**System prompt (abbreviated, full version in `prompts/show_director.md`):**

> You are the Creative Director for a professional fireworks display. You have been given a musical analysis and a client brief. Your job is to design the **narrative arc** of a show — not individual effects, but the emotional journey. You think in terms of tension and release, motif and variation, surprise and payoff. You are constrained by safety, budget tier, and the physical site. Output only valid JSON matching the provided schema. Be specific. "Epic chorus" is lazy; "twin silver-to-gold comet pairs rising on every downbeat of the chorus, left and right of center, growing to a triple on the last measure" is a plan.

---

### 7.4 `EffectLibrarianAgent`

**Purpose:** Given the `ShowPlan`, retrieves the top candidate effects from the catalog for each `PlanSection` and each `Motif`. Runs in parallel with the Choreographer.

**Uses:**
- SQLite catalog (seeded with ~500 effects, extensible to 20,000 via scraper).
- `sqlite-vec` for cosine similarity over bge-m3 embeddings of effect descriptions.
- Hard filters for allowed calibers, color, effect family, safety distance.

**Output:**

```python
class EffectCandidates(BaseModel):
    per_section: dict[int, list["RankedEffect"]]  # section index -> top 30
    per_motif: dict[str, list["RankedEffect"]]    # motif id -> top 10

class RankedEffect(BaseModel):
    effect_id: str
    score: float                                   # blend of semantic + rule match
    why: str                                       # 1-line explanation (for UI tooltip)
```

**Model:** No LLM. Embedding similarity + rule filter.
**Determinism:** Fully deterministic.
**Failure modes:** Empty result for a section → widens filters progressively, logs warning. Missing embedding column → rebuilds index on the fly.
**Tests:** Retrieval precision@10 on a hand-labeled set of 50 (section-description → expected-effect) pairs, target > 0.7.

---

### 7.4.a Catalog strategy — three-tier, legally clean

**This section exists because the agent MUST NOT scrape or redistribute proprietary manufacturer catalogs (Finale 3D supplier catalogs, FireOne catalogs, etc.). Violating this destroys the project.**

PyroMind's catalog is populated from three tiers, each with different legal treatment:

**Tier 1 — Generative (the default, the moat):**
Effects are synthesized on demand from text descriptions by a dedicated submodule `pyromind/catalog/vdl.py` implementing PyroMind's own Visual Design Language. This is PyroMind's own VDL — inspired by the general concept (text → simulation) that Finale and others use, but not reverse-engineered from any proprietary format. The generator uses the LLM to parse the description into structured parameters, then the physics model to produce the simulation. Every generated effect is stored with `source="generative"`, `license="pyromind-internal"`, `redistributable=true`.

**Tier 2 — User import:**
The user may import their own inventory (Excel/CSV/`.fdb`) that they own the rights to use. Importers live in `pyromind/catalog/importer.py`:
- `FinaleImporter` — accepts `.fdb` files (Finale 3D's open-documented effect database format) and Finale-format CSV with the standard column set (description, part number, category, subtype, duration, prefire, height, width, etc.).
- `FireOneImporter` — reads FireOne Pyro Digital CSV.
- `ExcelImporter` — generic spreadsheet with user-mapped columns.
- `CustomJSONImporter` — our own canonical format.

Imported effects are stored with `source="user_import:<filename>"`, `license="user_owned"`, `redistributable=false`. They work locally but are stripped from any exported share bundle or cloud backup.

**Tier 3 — Partner catalogs:**
Manufacturers can opt into hosting a catalog inside PyroMind via signed partnership (tracked in `data/partnerships.yaml` with the manufacturer's written permission email archived in `data/partnerships/<manufacturer>/`). Initial target partners (not to be pursued by the agent — Noor handles these conversations): any manufacturer Noor already has a relationship with through the Jordan/Middle East fireworks industry. Partner catalogs are stored with `source="partner:<name>"`, `license="<as-agreed>"`, `redistributable=<as-agreed>`.

**Schema addition — every `effects` row must include:**

```python
class Effect(BaseModel):
    # ... existing fields ...
    source: str                               # "generative" | "user_import:..." | "partner:..."
    license: str                              # "pyromind-internal" | "user_owned" | partner-specific
    provenance_url: str | None
    redistributable: bool
    imported_at: datetime
    importer_version: str                     # for re-migration
```

**What the agent MUST NOT do:**
- Scrape finale3d.com, its supplier catalog pages, or any manufacturer's website for effect data.
- Reverse-engineer Finale 3D's proprietary VDL effect definitions or simulation engine.
- Bundle effect data obtained from any source other than those three tiers.
- Use manufacturer names or SKUs in the seed catalog — seed catalog entries are generic ("3in red peony", not "Raccoon RAC-3001").

**What the agent MUST do:**
- Implement full `.fdb` import (format is documented by Finale on their site).
- Implement FireOne CSV import (format is documented).
- Write a PyroMind VDL parser/generator in `pyromind/catalog/vdl.py` as its own language, from scratch, based on the physics model we define — not copied from Finale's VDL.
- Make the 50-effect seed catalog entirely generic, manufacturer-neutral, and PyroMind-authored.

**Tests:**
- `.fdb` import round-trip on a synthetic test file we construct (not a real manufacturer's file).
- FireOne CSV round-trip on a synthetic file.
- Generative VDL: 20 reference descriptions produce simulations within physical plausibility bounds (apogee height, duration, particle count all within expected ranges).
- Legal check: `assert all(e.source != "partner:..." or e.license in approved_partner_licenses for e in effects)` runs in CI.

---

### 7.5 `ChoreographerAgent`

**Purpose:** The beating heart. Turns `ShowPlan` + `AudioAnalysis` + `EffectCandidates` into a time-aligned `Choreography` — a sequence of effect instances with precise timestamps, positions, and parameters.

**Produces `Choreography`:**

```python
class Choreography(BaseModel):
    events: list["ChoreographyEvent"]

class ChoreographyEvent(BaseModel):
    t_s: float                                 # firing time on the music
    effect_id: str                             # from catalog
    position: tuple[float, float, float]       # (x, y, z) meters on site coords
    caliber_in: int
    angle_deg: tuple[float, float]             # azimuth, elevation
    tag_motif: str | None
    tag_audio_event: str | None                # "downbeat", "vocal_onset", etc.
    reason: str                                # 1-line rationale
```

**Strategy (hybrid — this is key):**
1. **Rule-based skeleton** first. For each beat/downbeat/onset in the audio, decide if it should get an effect based on: current section's density target, current energy, last-effect cooldown, motif rules.
2. **LLM refinement pass** second. Send the skeleton + the surrounding audio context + candidate effects to the LLM with the instruction: "Here is a mechanical choreography. Make it *musical*. Swap effects where the type doesn't match the instrument that's playing. Add fills. Build tension. Respect the motifs."
3. **Validation pass** third: no two events within 50ms at the same position, total effect count matches budget_distribution ±5%, no forbidden effect families in their disallowed sections.

**Model:** Local Qwen2.5 32B primary, Claude Sonnet 4.5 fallback. This is the most important LLM call in the pipeline — worth spending tokens.
**Determinism:** Seeded stochastic. Rule pass is deterministic; LLM pass is seeded.
**Failure modes:** Budget overrun → rejects lowest-priority events until in budget. LLM returns invalid positions → clamp to site bounds with warning.
**Tests:** (a) Every event's `t_s` is within 20ms of a detected beat/onset. (b) No events outside site bounds. (c) Motif rules satisfied on 10 golden inputs.

---

### 7.6 `EffectCasterAgent`

**Purpose:** Expands the abstract `Choreography` into a concrete **firing script** — the actual hardware-ready sequence with cue numbers, device assignments, and prefire times.

**Produces `FiringScript`:**

```python
class FiringScript(BaseModel):
    cues: list["Cue"]
    devices: list["FiringDevice"]
    total_shell_count: int
    estimated_smoke_level: float              # for outdoor/indoor warnings
    duration_s: float

class Cue(BaseModel):
    cue_number: int                           # 1-indexed, gap-free
    fire_time_s: float                        # on the music
    prefire_ms: int                           # 100-400 typical for aerial
    effect_id: str
    device_id: str
    pin: int                                  # slat/pin on the module
    angle_deg: tuple[float, float]
    note: str
```

**Logic:**
- Read effect's `lift_time_ms` and `burst_delay_ms` from catalog → compute prefire.
- Pack events onto physical modules respecting pin count and reload times.
- Assign cue numbers in firing order, not musical order.
- Minimum 50ms between cues on the same module (hardware constraint).

**Model:** None. Pure logic. (An optional LLM "optimizer" pass may be added in Phase 8.)
**Determinism:** Fully deterministic.
**Failure modes:** Insufficient devices for count → error with suggested device additions. Negative fire_time after prefire subtraction → flag as "this effect cannot fire this early, start the show later."
**Tests:** Conservation (every choreography event becomes exactly one cue), cue numbers gap-free, no module overlap violations.

---

### 7.7 `SafetyAuditorAgent`

**Purpose:** Independent adversarial check. Reads the `FiringScript` fresh (doesn't trust upstream) and reports every safety violation.

**Produces `SafetyReport`:**

```python
class SafetyReport(BaseModel):
    passed: bool
    violations: list["Violation"]
    warnings: list["Violation"]
    stats: dict[str, float]                   # max_concurrent_shells, peak_noise_db, etc.

class Violation(BaseModel):
    severity: Literal["error", "warning"]
    code: str                                 # e.g., "SD_001_SAFETY_DISTANCE"
    message: str
    cue_numbers: list[int]
    suggested_fix: str
```

**Checks (non-exhaustive):**
- Every effect's debris fallout radius fits inside the site.
- Minimum safety distance to nearest audience barrier (NFPA 1123 table or equivalent).
- No two large-caliber (6"+) shells firing within 200ms (concussion limit).
- No effect above site ceiling.
- Wind direction field (from user) doesn't push debris into audience.
- Cumulative noise model doesn't exceed local permit (user-provided dB ceiling).
- No banned effect chemistry for the site's permit class.

**Model:** None. All rules codified as unit-testable functions. This agent is **intentionally dumb** and rule-based. No LLM judgment on safety.
**Determinism:** Fully deterministic.
**Failure modes:** A violation with `severity="error"` halts the pipeline. User must revise (via `ShowDirector` chat) or override with explicit acknowledgment.
**Tests:** Every violation code has a dedicated test with a script that triggers it.

---

### 7.8 `SimulatorAgent`

**Purpose:** Hands the firing script off to the frontend R3F scene with a pre-baked particle animation plan (so playback is buttery at 60fps without per-frame physics). Also can render to MP4 server-side.

**Produces `SimulationArtifact`:**

```python
class SimulationArtifact(BaseModel):
    particle_plan_json_path: str              # optimized for R3F consumption
    mp4_preview_path: str | None              # None if not rendered yet
    duration_s: float
    peak_particle_count: int
```

**How:**
1. For each cue, run the physics model forward: ballistic trajectory of shell, burst at apogee, star particles with drag + gravity + color curves.
2. Bake all particle positions into a keyframed array (60 fps).
3. For MP4: render with Three.js headless (Puppeteer + `three-headless`) or fall back to ffmpeg compositing of pre-rendered effect sprites.

**Model:** None.
**Determinism:** Fully deterministic.
**Failure modes:** Headless render fails → serve the plan JSON only; UI still plays it.
**Tests:** Particle count sanity, duration matches firing script, visual regression via Playwright screenshot on fixed frames.

---

### 7.9 `ExporterAgent`

**Purpose:** Turns the firing script into industry-standard formats. Also owns the *import* path for moving shows between PyroMind and other pro software (symmetric capability — see 7.4.a).

**Exports:**
- `show.pyromind.json` — canonical, full state.
- `show.fireone.csv` — FireOne Pyro Digital format.
- `show.finale.csv` — Finale 3D-importable CSV (their documented column schema).
- `show.preview.mp4` — the baked simulation (from `SimulatorAgent`).
- `show.cuesheet.pdf` — human-readable cue sheet for the operator.

**Imports (counterpart, lives in `catalog/importer.py` and `exporters/show_importer.py`):**
- `.fdb` files → PyroMind show + effects.
- Finale CSV → PyroMind show + effects.
- FireOne CSV → PyroMind show + effects.

**Model:** None.
**Determinism:** Fully deterministic.
**Tests:** Round-trip (import our FireOne CSV and Finale CSV into their respective parsers) preserves all cues; import synthetic Finale `.fdb` → edit in PyroMind → export Finale CSV → re-import produces equivalent show.

---

### 7.10 `CriticAgent`

**Purpose:** A second LLM pass that critiques the final show before the user sees it and suggests revisions. Runs in "read-only review" mode — does not modify, only reports.

**Produces `Critique`:**

```python
class Critique(BaseModel):
    overall_score: float                      # 0-10
    dimensions: dict[str, float]              # musicality, visual_balance, pacing, safety_margin, variety, wow_factor
    strengths: list[str]
    weaknesses: list[str]
    suggested_revisions: list[str]            # plain-language, user can one-click apply
```

**Model:** Claude Sonnet 4.5 preferred (this is where cloud is worth it), Qwen2.5 fallback.
**Determinism:** Stochastic, seeded.
**Failure modes:** Timeout → skip critique, show proceeds without it (non-blocking).
**Tests:** Score correlation with human ratings on 10 hand-evaluated shows, target Spearman > 0.6.

---

## 8. Execution plan — phases

**Each phase ends with a self-test gate. Do not proceed until green.**

### Phase 0 — Inventory & skeleton (1 day)
- Clone repo, produce `docs/legacy_inventory.md`.
- Create new folder structure from Section 6.
- Move old code into `legacy/`.
- Set up Tauri + React + Python sidecar "hello world" (sidecar returns `{"status":"ok"}` on `/health`, frontend displays it).
- Wire up CI.
- **Gate:** `pnpm tauri dev` opens a window that shows "Sidecar OK" on all three OSes. CI passes lint on empty project.

### Phase 1 — Data layer (2 days)
- SQLite schema for effects, catalogs, projects, shows.
- `sqlite-vec` integration.
- Pydantic models for every type in Section 7.
- Seed catalog (~50 hand-curated effects is enough to start; 500 by Phase 5).
- **Gate:** `pytest backend/tests/catalog` green; can query effects via REST.

### Phase 2 — Audio analyst (3 days)
- Full `AudioAnalystAgent` with all sub-pipelines.
- Model download script (Demucs, MERT, CLAP) with progress UI.
- Cache by SHA256 of audio bytes.
- **Gate:** End-to-end analysis of 5 fixture songs produces golden JSON matching reference within tolerance.

### Phase 3 — The graph & orchestrator (2 days)
- LangGraph with 9 agent stubs (all return valid-shape fake data).
- Checkpoint store in SQLite.
- WebSocket event stream with typed events.
- Human-in-the-loop interrupt after `SafetyAuditor`.
- **Gate:** Full graph runs end-to-end with stubs; frontend receives every agent's progress over WS.

### Phase 4 — Show director + effect librarian (3 days)
- Ollama integration, prompt library, JSON-schema-guided output.
- Few-shot example corpus (10 reference plans).
- Embedding index build + retrieval.
- **Gate:** For 5 fixture songs, produce plans with section-energy Pearson > 0.5 and retrieval precision@10 > 0.7.

### Phase 5 — Choreographer + effect caster + safety auditor (4 days)
- Rule-based skeleton generator.
- LLM refinement with strict JSON output.
- Cue packing algorithm.
- Full safety ruleset (at least 15 codified checks).
- **Gate:** Golden choreographies for 5 songs pass all 3 test classes (timing, bounds, motifs); safety violations trigger on hand-crafted bad scripts.

### Phase 6 — 3D simulator + timeline UI (4 days)
- R3F scene with site ground plane, launch positions, audience barrier.
- Particle system with color curves.
- DAW-style timeline with audio waveform, beat grid, event markers, drag-to-reposition.
- Playback synced to audio within ±10ms.
- **Gate:** A full show plays in the UI with accurate timing; manual edits re-run only from `EffectCaster` downward (not the whole pipeline).

### Phase 7 — Exporter + critic + chat revisions (2 days)
- All four export formats.
- MP4 render (headless R3F or ffmpeg fallback).
- `AgentChatPanel` for revision requests; routes back into `ShowDirector` with the existing state as context.
- **Gate:** Exports import back into our own parsers round-trip; a request like "make the finale bigger" changes the plan and only re-runs downstream.

### Phase 8 — Polish, i18n, packaging, docs (3 days)
- Full Arabic translation.
- RTL testing.
- Signed Windows + Mac builds.
- User manual (docs/user-guide.md).
- Auto-updater.
- Crash reporting (Sentry, self-hosted).
- **Gate:** Someone who has never seen the app can install it, load a song, and export a show in under 15 minutes.

**Total target: ~24 working days.** Extensions welcomed; compressions not.

---

## 9. Testing philosophy

- **Golden files are king.** Every LLM agent has 5 reference songs with hand-blessed expected outputs. The test isn't "exact match" — it's structured similarity (same sections, same plan intent, same motif count ±1, retrieval overlap > 60%). When an LLM update breaks goldens, a human reviews and updates the golden if the new output is genuinely better.
- **Property tests on pure logic.** Hypothesis-generated firing scripts fed to SafetyAuditor must never report a false negative on a hand-crafted violation.
- **Visual regression.** Playwright screenshots of the simulation at fixed frames compared with SSIM > 0.95.
- **Performance budgets.** Full pipeline on a 4-minute song must complete in < 10 minutes on a reference machine (M2 Pro or RTX 3080 equivalent). CI fails on regression > 20%.

---

## 10. Data & ethics

- **Effect catalog sources** must have a tracked provenance column (`source_url`, `license`, `scraped_at`). WikiFireworks is generally user-contributed; do not ship anyone's proprietary catalog without permission.
- **Sample songs in fixtures must be CC0.** No copyrighted music in the repo. The app obviously processes the user's own files locally — that's their problem to have rights for.
- **Cloud LLM calls** must be opt-in, with a clear settings toggle, and must never send the user's audio bytes — only derived analysis JSON (which the user can preview before sending).
- **Telemetry:** opt-in only, aggregate only (agent timings, error rates, no audio, no show contents).

---

## 11. For the agent: how to ask for help

When you get stuck, **do not silently degrade the spec**. Create `docs/proposals/NNN-your-question.md` with:

1. What you're trying to do.
2. What's blocking you.
3. Two or three options you considered.
4. Your recommendation.

Then stop and wait. Noor will read it and decide.

Do **not** hallucinate library APIs. When you're unsure of a library's current API surface, read the actual installed source (`python -c "import X; help(X)"` or `node_modules/X/dist/index.d.ts`) before writing code against it.

Do **not** skip tests to "make progress." A missing test is a regression waiting to land.

Do commit often, with descriptive messages. Every agent's introduction is its own commit. Every bug fix references a test.

---

## 12. Definition of done

PyroMind is "done" (v1.0) when:

1. A user can drop `any_song.mp3` into the app and, in under 10 minutes, get a 3D simulated show that plays in sync with the audio.
2. The show can be exported to FireOne CSV and imported successfully into a mock FireOne parser that ships in our test suite.
3. The full pipeline runs offline after initial model download.
4. The UI is available in English and Arabic (RTL correct).
5. Signed installers exist for Windows and macOS.
6. `README.md` has a 2-minute demo GIF.
7. CI is green on main.
8. At least 10 reference songs have golden outputs in the test suite.
9. The SafetyAuditor has at least 15 codified checks, each with a dedicated test.
10. The project's own `PYROMIND_AGENT_BUILD_SPEC.md` is kept in the repo and updated as reality diverges from this spec (every divergence gets an ADR).

---

*End of spec. Noor: hand this file to your agent and tell it to start at Phase 0.*
