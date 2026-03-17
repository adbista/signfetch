from __future__ import annotations

from pathlib import Path
import json
import os
import socketserver
import subprocess
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler

import pytest


class SignpostingHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_HEAD(self) -> None:
        if self.path == "/record":
            self.send_response(200)
            self.send_header(
                "Link",
                "</files/a.csv>; rel=\"item\", </linkset.json>; rel=\"linkset\"; type=\"application/linkset+json\"",
            )
            self.end_headers()
            return
        if self.path == "/record-content":
            self.send_response(200)
            self.send_header("Link", "</files/content>; rel=\"item\"")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/record":
            body = "<html><head><link rel=\"item\" href=\"/files/b.json\" type=\"application/json\"></head></html>"
            self.send_response(200)
            self.send_header(
                "Link",
                "</linkset.json>; rel=\"linkset\"; type=\"application/linkset+json\"",
            )
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/record-content":
            body = "<html></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/linkset.json":
            payload = json.dumps({"linkset": [{"item": [{"href": "/files/c.txt", "type": "text/plain"}]}]})
            self.send_response(200)
            self.send_header("Content-Type", "application/linkset+json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        if self.path == "/files/a.csv":
            content = b"alpha"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=\"data-a.csv\"")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if self.path == "/files/b.json":
            content = b"{\"value\": 1}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if self.path == "/files/c.txt":
            content = b"gamma"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if self.path == "/files/content":
            content = b"opaque"
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_response(404)
        self.end_headers()


@pytest.fixture(scope="module")
def server_base_url() -> str:
    with socketserver.TCPServer(("127.0.0.1", 0), SignpostingHandler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server.shutdown()
            thread.join()


SCENARIOS = {
    "scenario-1": {
        "target": "/record-content",
        "expect_zip": True,
        "files": {},
    },
    "scenario-2": {
        "target": "/record",
        "expect_zip": False,
        "files": {
            "data-a.csv": b"alpha",
            "b.json": b"{\"value\": 1}",
            "c.txt": b"gamma",
        },
    },
}


def _selected_scenarios() -> list[str]:
    scenario = os.environ.get("E2E_SCENARIO")
    if scenario:
        return [scenario]
    return list(SCENARIOS.keys())


@pytest.mark.e2e
@pytest.mark.parametrize("scenario", _selected_scenarios())
def test_examples_run(tmp_path: Path, server_base_url: str, scenario: str) -> None:
    settings = SCENARIOS[scenario]
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "examples" / scenario / "run.py"

    output_dir = tmp_path / scenario
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["SIGNFETCH_TARGET"] = f"{server_base_url}{settings['target']}"
    env["SIGNFETCH_OUTPUT"] = str(output_dir)

    subprocess.run([sys.executable, str(script_path)], check=True, cwd=repo_root, env=env)

    if settings["expect_zip"]:
        archive_path = output_dir / "content.zip"
        assert archive_path.exists()
        with zipfile.ZipFile(archive_path, "r") as archive:
            assert archive.namelist() == ["payload"]
            assert archive.read("payload") == b"opaque"
        return

    for name, payload in settings["files"].items():
        assert (output_dir / name).read_bytes() == payload
