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
        if self.path == "/record-2":
            self.send_response(200)
            self.send_header("Link", "</files/opaque>; rel=\"item\"")
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
        if self.path == "/record-2":
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
        if self.path == "/files/opaque":
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


@pytest.mark.e2e
def test_examples_run(tmp_path: Path, server_base_url: str) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scenario_one = repo_root / "examples" / "scenario-1" / "run.py"
    scenario_two = repo_root / "examples" / "scenario-2" / "run.py"

    output_one = tmp_path / "scenario-1"
    output_two = tmp_path / "scenario-2"
    output_one.mkdir(parents=True, exist_ok=True)
    output_two.mkdir(parents=True, exist_ok=True)

    env_one = os.environ.copy()
    env_one["SIGNFETCH_TARGET"] = f"{server_base_url}/record"
    env_one["SIGNFETCH_OUTPUT"] = str(output_one)

    env_two = os.environ.copy()
    env_two["SIGNFETCH_TARGET"] = f"{server_base_url}/record-2"
    env_two["SIGNFETCH_OUTPUT"] = str(output_two)

    subprocess.run([sys.executable, str(scenario_one)], check=True, cwd=repo_root, env=env_one)
    subprocess.run([sys.executable, str(scenario_two)], check=True, cwd=repo_root, env=env_two)

    assert (output_one / "data-a.csv").read_bytes() == b"alpha"
    assert (output_one / "b.json").read_bytes() == b"{\"value\": 1}"
    assert (output_one / "c.txt").read_bytes() == b"gamma"

    archive_path = output_two / "opaque.zip"
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, "r") as archive:
        assert archive.namelist() == ["payload"]
        assert archive.read("payload") == b"opaque"
