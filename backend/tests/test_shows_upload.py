"""Multipart POST /shows upload behavior."""

from __future__ import annotations

import io
import wave

from fastapi.testclient import TestClient


def _tiny_wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 80)
    return buf.getvalue()


def test_post_shows_accepts_wav(client: TestClient) -> None:
    proj = client.post("/projects", json={"name": "Upload"}).json()
    pid = proj["id"]
    wav = _tiny_wav_bytes()
    response = client.post(
        "/shows/",
        data={"project_id": pid, "language": "en"},
        files={"song": ("clip.wav", wav, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "show_id" in body
    assert body.get("status") == "analyzing"


def test_post_shows_rejects_mp4(client: TestClient) -> None:
    proj = client.post("/projects", json={"name": "Bad"}).json()
    pid = proj["id"]
    response = client.post(
        "/shows/",
        data={"project_id": pid},
        files={"song": ("clip.mp4", b"\x00\x01\x02", "video/mp4")},
    )
    assert response.status_code == 422


def test_post_shows_saves_file(client: TestClient) -> None:
    from pyromind import config as cfg_mod

    proj = client.post("/projects", json={"name": "Disk"}).json()
    pid = proj["id"]
    root = cfg_mod.settings.projects_root()
    wav = _tiny_wav_bytes()
    response = client.post(
        "/shows/",
        data={"project_id": pid},
        files={"song": ("song.wav", wav, "audio/wav")},
    )
    assert response.status_code == 200
    dest = root / pid / "song.wav"
    assert dest.is_file()
    assert dest.read_bytes() == wav
