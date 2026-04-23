//! Spawn the Python FastAPI sidecar on an OS-assigned free port.

use std::io;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

/// Holds the sidecar child process so it is not dropped (which would kill the server).
pub struct SidecarRuntime {
    /// TCP port uvicorn binds to (`127.0.0.1:<port>`).
    pub port: u16,
    /// Wrapped for `Send + Sync` so this type can live in Tauri `State` on all platforms.
    _child: Mutex<Child>,
}

/// Bind `127.0.0.1:0`, read the assigned port, then release the listener.
fn allocate_sidecar_port() -> Result<u16, io::Error> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    drop(listener);
    Ok(port)
}

fn backend_dir() -> Result<PathBuf, io::Error> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    // Crate lives at frontend/src-tauri; Python backend is repo-root/backend.
    let candidates = [
        manifest_dir.join("../../backend"),
        manifest_dir.join("../backend"),
        PathBuf::from("../../backend"),
        PathBuf::from("../backend"),
    ];

    for candidate in candidates {
        if candidate.exists() {
            return Ok(candidate);
        }
    }

    Err(io::Error::new(
        io::ErrorKind::NotFound,
        "Could not locate backend directory for sidecar",
    ))
}

fn venv_python_path(backend: &PathBuf) -> PathBuf {
    if cfg!(windows) {
        backend.join(".venv").join("Scripts").join("python.exe")
    } else {
        backend.join(".venv").join("bin").join("python")
    }
}

/// Spawn uvicorn with `PYROMIND_SIDECAR_PORT` set; returns the port and child handle.
pub fn start_sidecar() -> Result<SidecarRuntime, io::Error> {
    let port = allocate_sidecar_port()?;
    let backend = backend_dir()?;
    let venv_python = venv_python_path(&backend);

    let mut command = if venv_python.exists() {
        let mut cmd = Command::new(venv_python);
        cmd.arg("main.py");
        cmd
    } else if cfg!(windows) {
        let mut cmd = Command::new("python");
        cmd.arg("main.py");
        cmd
    } else {
        let mut cmd = Command::new("python3");
        cmd.arg("main.py");
        cmd
    };

    command
        .current_dir(&backend)
        .env("PYROMIND_SIDECAR_PORT", port.to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    let child = command.spawn()?;
    Ok(SidecarRuntime {
        port,
        _child: Mutex::new(child),
    })
}
