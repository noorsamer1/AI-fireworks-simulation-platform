# PyroMind — Architecture

Companion to `PYROMIND_AGENT_BUILD_SPEC.md`. Diagrams and deeper explanation of the moving parts.

## 1. System overview

```mermaid
flowchart TB
    subgraph Shell["Tauri Shell (Rust)"]
        TauriMain["main.rs"]
        Commands["IPC commands"]
        Sidecar["sidecar.rs<br/>(spawns + health-checks Python)"]
    end

    subgraph FE["React Frontend"]
        Workspace["Project Workspace"]
        SimView["Simulation View<br/>(React Three Fiber)"]
        Timeline["DAW Timeline"]
        ChatPanel["Agent Chat Panel"]
        ExportWiz["Export Wizard"]
    end

    subgraph BE["Python Sidecar (FastAPI)"]
        Router["REST + WS routes"]
        Graph["LangGraph<br/>9 Agents"]
        Catalog["SQLite + sqlite-vec<br/>Effect Catalog"]
        Physics["Physics + Bake"]
        Exporters["FireOne / Finale / JSON / MP4 / PDF"]
    end

    subgraph Models["Models (local-first)"]
        Ollama["Ollama<br/>Qwen 2.5 32B"]
        Demucs["Demucs v4"]
        MERT["MERT-v1-330M"]
        CLAP["CLAP (LAION)"]
        Cloud["Claude 4.5<br/>(opt-in fallback)"]
    end

    TauriMain --> Commands --> Sidecar
    Sidecar -.spawns.-> Router
    FE <-- REST --> Router
    FE <== WebSocket ==> Router
    Router --> Graph
    Graph --> Catalog
    Graph --> Physics
    Graph --> Exporters
    Graph --> Ollama
    Graph --> Demucs
    Graph --> MERT
    Graph --> CLAP
    Graph -.fallback.-> Cloud
```

## 2. Agent graph (LangGraph)

```mermaid
flowchart LR
    START([Song + Constraints]) --> AA[AudioAnalyst]
    AA --> SD[ShowDirector]
    SD --> EL[EffectLibrarian]
    SD --> CH[Choreographer]
    EL --> CH
    CH --> EC[EffectCaster]
    EC --> SA{SafetyAuditor}
    SA -->|pass| SIM[Simulator]
    SA -->|fail| SD
    SIM --> CR[Critic]
    CR --> HIL{Human review?}
    HIL -->|revise| SD
    HIL -->|approve| EXP[Exporter]
    EXP --> END([Show + exports on disk])

    style SA fill:#ff6b6b,color:#fff
    style HIL fill:#ffd93d,color:#000
    style CR fill:#6bcfff,color:#000
```

## 3. State lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: User drops song
    Created --> Analyzing: Orchestrator starts
    Analyzing --> Planning: audio populated
    Planning --> Retrieving: plan populated
    Retrieving --> Choreographing: candidates populated
    Choreographing --> Casting: choreography populated
    Casting --> Auditing: firing_script populated
    Auditing --> Simulating: safety.passed == true
    Auditing --> Planning: safety.passed == false (auto-revise)
    Simulating --> Critiquing: simulation populated
    Critiquing --> HumanReview: critique populated
    HumanReview --> Planning: user requests revision
    HumanReview --> Exporting: user approves
    Exporting --> Done: exports populated
    Done --> [*]
```

Every transition writes a checkpoint to SQLite. Any phase can be resumed after crash.

## 4. Catalog architecture — the three-tier strategy

PyroMind does **not** bundle anyone else's proprietary catalog. Instead, it uses a three-tier model:

```mermaid
flowchart TB
    subgraph T1["Tier 1: Generative (Default)"]
        Desc["Text description<br/>'3in red peony w/ silver tail'"]
        VDL["PyroMind VDL<br/>(LLM + physics synthesis)"]
        Sim["Simulation + metadata"]
        Desc --> VDL --> Sim
    end

    subgraph T2["Tier 2: User Import"]
        UserFDB["User's own .fdb / CSV"]
        UserInv["User's inventory spreadsheet"]
        Importer["Importer<br/>(Finale 3D / FireOne / custom)"]
        UserCat["User's personal catalog"]
        UserFDB --> Importer
        UserInv --> Importer
        Importer --> UserCat
    end

    subgraph T3["Tier 3: Partner Catalogs"]
        Partner["Signed partnership<br/>(manufacturer opts in)"]
        Host["Hosted catalog<br/>(attribution required)"]
        Sub["User subscribes<br/>(opt-in per catalog)"]
        Partner --> Host --> Sub
    end

    T1 --> UnifiedDB[(Unified Effect DB<br/>+ provenance column)]
    T2 --> UnifiedDB
    T3 --> UnifiedDB

    UnifiedDB --> Librarian[EffectLibrarian Agent]
```

**Legal tracking:** every effect in the DB has `source`, `license`, `provenance_url`, and `redistributable: bool` columns. The `EffectLibrarian` respects these — an effect marked `redistributable: false` can be used locally but is stripped from any exported share bundle.

### 4.1 Catalog SQLite schema (ER)

Phase 1 ships two tables: `effects` (authoritative rows + provenance) and `effects_vec` (placeholder for `sqlite-vec` embeddings; `embedding_json` is a stopgap until the vector extension is wired).

```mermaid
erDiagram
    EFFECTS {
        text effect_id PK
        text name
        text description
        text family
        text colors
        int caliber_in
        real duration_s
        real height_m
        real safety_distance_m
        text source
        text license
        text provenance_url
        int redistributable
        text imported_at
        text importer_version
    }

    EFFECTS_VEC {
        text effect_id PK
        text embedding_json
    }

    EFFECTS ||--o| EFFECTS_VEC : "optional embedding row"
```

## 5. Finale 3D interoperability (strict legal bounds)

PyroMind interoperates with Finale 3D **through the user**, never by copying Finale's catalog:

- **Import (allowed):** Read a user's `.fdb` file or Finale-format CSV that they own a license for. Open formats that Finale itself documents for import. Map fields to our canonical schema.
- **Export (allowed):** Write a Finale-importable CSV so the user can move their PyroMind-designed show into Finale if they want.
- **VDL (allowed):** We define our own PyroMind VDL inspired by the same *concept* Finale uses (text description → simulation), but we do not use Finale's proprietary VDL strings or reverse-engineer their simulation engine.
- **Catalogs (not allowed without partnership):** We do not ship, scrape, mirror, or otherwise redistribute Raccoon, Wizard, Spirit of '76, Dominator, Lidu, NICO, Marti, Parente, RES Pyro, or any other manufacturer's catalog as hosted in Finale Inventory. Users who subscribe to those inside Finale 3D can export their *own* imported effects file and bring it into PyroMind for personal use.

## 6. Inside the AudioAnalyst

```mermaid
flowchart LR
    Audio["song.wav"] --> Load["Load + LUFS normalize"]
    Load --> Demucs_["Demucs v4<br/>stem separation"]
    Demucs_ --> Stems["drums, bass,<br/>vocals, other"]

    Load --> Beats["madmom<br/>downbeat tracker"]
    Load --> Onsets["librosa<br/>onset detection"]
    Load --> Essentia_["essentia<br/>mood, energy, key"]

    Stems --> PerStem["Per-stem onsets"]

    Load --> MERT_["MERT-v1-330M<br/>5s windows"]
    Load --> CLAP_["CLAP<br/>2s windows"]
    MERT_ --> Sections["Structural<br/>segmentation"]

    Beats --> Analysis[(AudioAnalysis)]
    Onsets --> Analysis
    PerStem --> Analysis
    Essentia_ --> Analysis
    Sections --> Analysis
    MERT_ --> Analysis
    CLAP_ --> Analysis

    Analysis --> Cache[(SHA256 cache)]
```

## 7. Inside the Choreographer — hybrid strategy

```mermaid
flowchart TB
    In["AudioAnalysis +<br/>ShowPlan +<br/>EffectCandidates"] --> Rule["Rule skeleton<br/>(deterministic)"]
    Rule --> Skeleton["Skeleton events<br/>beat-aligned, rule-satisfying"]
    Skeleton --> LLM["LLM refinement pass<br/>Qwen 32B / Claude 4.5"]
    LLM --> Refined["Musically-refined<br/>choreography"]
    Refined --> Validate{"Validator"}
    Validate -->|fail| Reject["Reject + re-run LLM<br/>(max 2 retries)"]
    Validate -->|pass| Out["Choreography"]
    Reject --> LLM
```

The rule pass guarantees correctness. The LLM pass adds musicality. The validator guarantees nothing the LLM did broke correctness.

## 8. Safety — intentionally dumb and rule-based

```mermaid
flowchart LR
    FS["FiringScript"] --> Checks["15+ rule checks<br/>in pure Python"]
    Checks --> SD_001["SD_001: Safety distance"]
    Checks --> SD_002["SD_002: Site ceiling"]
    Checks --> SD_003["SD_003: Debris radius"]
    Checks --> SD_004["SD_004: Concussion spacing"]
    Checks --> SD_005["SD_005: Wind debris"]
    Checks --> SD_006["SD_006: Cumulative noise"]
    Checks --> SD_007["SD_007: Caliber limits"]
    Checks --> SD_008["..."]
    SD_001 --> Report[(SafetyReport)]
    SD_002 --> Report
    SD_003 --> Report
    SD_004 --> Report
    SD_005 --> Report
    SD_006 --> Report
    SD_007 --> Report
    SD_008 --> Report
```

No LLM sees this step. Safety is too high-stakes for stochastic output.

## 9. Physical deployment on user's machine

```mermaid
flowchart TB
    subgraph UserMachine["User's Desktop (Mac or Windows)"]
        App["PyroMind.app / PyroMind.exe"]
        App --> WebView["WebView2 / WKWebView<br/>React UI"]
        App --> Py["Python sidecar<br/>localhost:random_port"]

        subgraph AppData["AppData / Application Support"]
            DB[("catalog.sqlite")]
            Projects[("projects/")]
            Cache[("model cache/")]
            Models[("ollama models/")]
        end

        Py --> DB
        Py --> Projects
        Py --> Cache
        Py -.spawns.-> OllamaProc["ollama serve"]
        OllamaProc --> Models
    end

    UserMachine -.optional.-> Internet[("api.anthropic.com<br/>(only if cloud fallback enabled)")]
```

The app is 100% functional after first-run with internet off.

## 10. Data contracts — the single source of truth

All cross-agent data types are defined in `backend/pyromind/models/*.py` as Pydantic models. A build step (`scripts/gen_types.py`) converts them to TypeScript interfaces in `frontend/src/types/generated.ts`. Both sides import from the same schema. If you change a type on one side without regenerating, CI fails.

```mermaid
flowchart LR
    Py["Pydantic models<br/>(backend source of truth)"] --> GenScript["scripts/gen_types.py"]
    GenScript --> TS["TypeScript types<br/>(frontend, auto-generated)"]
    TS --> FE["Frontend code"]
    Py --> BE["Backend code"]

    style Py fill:#3776ab,color:#fff
    style TS fill:#3178c6,color:#fff
```

---

*Changes to architecture require an ADR in `docs/decisions/`. Every ADR has a number, a date, a status (proposed/accepted/superseded), and the tradeoffs considered.*
