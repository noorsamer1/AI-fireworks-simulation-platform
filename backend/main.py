"""Run the PyroMind FastAPI sidecar."""

import os

import uvicorn


def main() -> None:
    """Start the sidecar server."""
    port = int(os.environ.get("PYROMIND_SIDECAR_PORT", "8765"))
    uvicorn.run(
        "pyromind.api.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
