"""Real ASGI HTTP/WebSocket contracts with an isolated fake agent executable."""
import json
import os
import sys
import time

from fastapi.testclient import TestClient

from app.auth.service import hash_password
from app.auth.setup_user import write_credentials_file
from app.config import get_settings
from app.main import create_app


def test_authenticated_create_run_live_history_and_edit_workflow(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    binary = tmp_path / "bin"
    binary.mkdir()
    agent = binary / "claude"
    agent.write_text(f"#!{sys.executable}\n" + '''import json,pathlib,time
print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'Working now'}]}}),flush=True)
time.sleep(0.5)
pathlib.Path('IMPLEMENTATION_PLAN.md').write_text('- [x] 1.1 Ready\\nSTATUS: COMPLETE\\n')
print(json.dumps({'type':'result','usage':{'input_tokens':12,'output_tokens':4},'result':'Ready'}),flush=True)
''')
    agent.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binary}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(root))
    credentials = tmp_path / "credentials.yaml"
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials))
    get_settings.cache_clear()
    write_credentials_file(credentials, "reviewer", hash_password("fixture-only-password"))
    with TestClient(create_app(frontend_dist=tmp_path / "no-frontend")) as client:
        assert client.get("/api/projects").status_code == 401
        login = client.post("/api/auth/login", json={"username": "reviewer", "password": "fixture-only-password"})
        assert login.status_code == 200
        tokens = login.json()
        client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
        assert client.get("/api/projects").json() == []  # Warm discovery before creation.
        created = client.post("/api/wizard/create", json={
            "project_name": "workflow", "cli": "claude", "model_override": "retained-model",
            "max_iterations": 1, "files": [
                {"path": "PROMPT.md", "content": "Build the fixture"},
                {"path": "IMPLEMENTATION_PLAN.md", "content": "- [ ] 1.1 Ready\n"},
            ],
        })
        assert created.status_code == 200, created.text
        project_id = created.json()["project_id"]
        prefix = f"/api/projects/{project_id}"
        assert client.get(prefix).status_code == 200
        assert client.get("/api/capabilities").json()["project_dirs"] == [str(root)]
        with client.websocket_connect("/api/ws") as socket:
            socket.send_json({"action": "authenticate", "token": tokens["access_token"]})
            assert socket.receive_json()["type"] == "authenticated"
            socket.send_json({"action": "subscribe", "projects": [project_id]})
            started = client.post(prefix + "/start", json={})
            assert started.status_code == 200, started.text
            event_types = set()
            for _ in range(30):
                event = socket.receive_json()
                event_types.add(event["type"])
                if event["type"] == "iteration_completed":
                    break
            assert {"log_append", "iteration_completed"} <= event_types
        for _ in range(100):
            if client.get(prefix).json()["status"] == "complete":
                break
            time.sleep(0.02)
        assert client.get(prefix).json()["status"] == "complete"
        log = client.get(prefix + "/log").json()
        assert "Working now" in log["text"]
        tail = client.get(prefix + "/log", params={"offset": log["offset"], "generation": log["generation"]}).json()
        assert tail["text"] == ""
        config = client.get(prefix + "/config").json()
        config["max_iterations"] = 2
        assert client.put(prefix + "/config", json=config).json()["model"] == "retained-model"
        plan = client.get(prefix + "/plan")
        plan_file = root / "workflow/IMPLEMENTATION_PLAN.md"
        plan_file.write_text("- [ ] 1.1 Concurrent change\n")
        conflict = client.put(prefix + "/plan", headers={"If-Match": plan.headers["etag"]}, json={"content": "Overwrite"})
        assert conflict.status_code == 412
        assert "Concurrent change" in plan_file.read_text()
        fresh = client.get(prefix + "/plan")
        saved = client.put(prefix + "/plan", headers={"If-Match": fresh.headers["etag"]}, json={"content": "Reviewed changes\n"})
        assert saved.status_code == 200
        records = root / "workflow/.ralph/iterations.jsonl"
        records.write_text("".join(json.dumps({"iteration": n, "max": 1000, "start": "2026-01-01T00:00:00Z", "status": "success"}) + "\n" for n in range(1, 602)))
        history = client.get(prefix + "/iterations?sort=desc&limit=500").json()
        assert history["total"] == 601
        assert history["iterations"][0]["number"] == 601
        older = client.get(prefix + "/iterations?sort=desc&limit=500&offset=500").json()
        assert older["iterations"][-1]["number"] == 1
        assert project_id in client.get("/api/projects/overview").json()
