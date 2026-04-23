# ADR-002: Windows native linker required for Tauri / Rust on MSVC target

## Status

Accepted

## Context

Rust was installed successfully (`rustc` / `cargo` via rustup). Running `cargo check` in `src-tauri/` failed with:

> `error: linker link.exe not found` — MSVC targets require the Visual C++ toolchain.

This blocks `pnpm tauri dev` / `pnpm tauri build` on Windows until **Visual Studio Build Tools** (or full VS) with the **Desktop development with C++** workload is installed, or an alternative target (e.g. `x86_64-pc-windows-gnu`) is adopted project-wide.

## Decision

- **Primary shell remains Tauri** (per spec). We do **not** switch to Electron solely because `link.exe` was missing in one environment.
- **Local Windows dev** must install MSVC build tools (documented in root `README.md` when added) before running Tauri builds.
- **CI** should use a Windows runner image that includes MSVC, or a matrix that builds Tauri only where the linker exists.

## Consequences

### Positive

- Keeps the architecture aligned with the spec (Tauri 2).

### Negative

- First-time Windows contributors hit an extra install step (Build Tools ~several GB).

## Alternatives considered

1. **Electron fallback (ADR-001 path)** — rejected for this failure mode; linker is a normal Windows prerequisite, not a “Rust blocked >1 day” situation.
2. **GNU toolchain only** — possible but adds maintenance (dual targets, different CI); defer unless MSVC install is impossible for the team.

## References

- `PYROMIND_AGENT_BUILD_SPEC.md` §4 (Tauri primary; Electron only if Rust blocks >1 day).
- Rust error output from `cargo check` in `src-tauri/` (linker `link.exe` not found).

## Appendix: Python settings binding (unrelated to MSVC, discovered during Phase 1 tests)

Modules that do `from pyromind.config import settings` bind the **initial** `Settings` instance at import time. Replacing `pyromind.config.settings` in tests then leaves those modules pointing at a stale object (symptom: row counts like 54 instead of 50). Prefer `import pyromind.config as _pm_config` and read `_pm_config.settings` at use sites (`catalog/db.py`, `api/main.py`, `llm.py` follow this pattern).
