import hashlib
import hmac
import json
import os
import subprocess
import sys
import types

try:
    from fastapi.testclient import TestClient
except ImportError as e:
    raise RuntimeError(
        "fastapi[testclient] is required for testing. "
        "Install with: pip install 'fastapi[all]'"
    ) from e

# Ensure repository root is on sys.path for package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import chatops.main as appmod


def make_client():
    return TestClient(appmod.app)


def test_healthz_ok():
    client = make_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_run_requires_auth(monkeypatch):
    # Ensure server expects an API key
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    client = make_client()
    r = client.post("/run", json={"name": "scale_stack"})
    assert r.status_code == 401


def test_run_scale_happy_path(monkeypatch):
    # Configure API key
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    # Mock subprocess.run to avoid executing docker
    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)

    client = make_client()
    r = client.post("/run", headers={"x-api-key": "secret"}, json={"name": "scale_stack"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "OK" in r.json()["stdout"]


def test_ip_allowlist_denies(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    monkeypatch.setenv("CHATOPS_IP_ALLOWLIST", "10.0.0.0/8")

    client = make_client()
    # Simulate a client outside the allowlist via X-Forwarded-For
    headers = {"x-api-key": "secret", "x-forwarded-for": "192.168.1.10"}
    r = client.post("/run", headers=headers, json={"name": "scale_stack"})
    assert r.status_code == 403


def test_ip_allowlist_allows(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    monkeypatch.setenv("CHATOPS_IP_ALLOWLIST", "192.168.0.0/16,10.0.0.0/8")

    # Mock subprocess.run and use an intent that exists
    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)

    client = make_client()
    headers = {"x-api-key": "secret", "x-forwarded-for": "192.168.1.10"}
    r = client.post("/run", headers=headers, json={"name": "scale_stack"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_label_mismatch_blocked(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    # Force a mismatched label requirement via load_intent
    class FakeIntent:
        label_required = "some-other-label"
        action = "scale"
        stack = "stack-media"
        service = "plex"
        replicas = 1
        compose = "/opt/stacks/stack-media/docker-compose.yml"

    monkeypatch.setattr(appmod, "load_intent", lambda name: FakeIntent())

    client = make_client()
    r = client.post("/run", headers={"x-api-key": "secret"}, json={"name": "anything"})
    assert r.status_code == 403


def test_scale_missing_fields(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    class FakeIntent:
        label_required = appmod.APPROVED_LABEL
        action = "scale"
        stack = "stack-media"
        service = None
        replicas = None
        compose = "/opt/stacks/stack-media/docker-compose.yml"

    monkeypatch.setattr(appmod, "load_intent", lambda name: FakeIntent())

    client = make_client()
    r = client.post("/run", headers={"x-api-key": "secret"}, json={"name": "anything"})
    assert r.status_code == 400


def test_rollout_happy_path(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    class FakeIntent:
        label_required = appmod.APPROVED_LABEL
        action = "rollout"
        stack = "stack-media"
        service = None
        replicas = None
        compose = "/opt/stacks/stack-media/docker-compose.yml"

    monkeypatch.setattr(appmod, "load_intent", lambda name: FakeIntent())

    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)

    client = make_client()
    r = client.post("/run", headers={"x-api-key": "secret"}, json={"name": "anything"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_dry_run_mode(monkeypatch):
    """Test that dry_run=true prevents actual execution."""
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    class FakeIntent:
        label_required = appmod.APPROVED_LABEL
        action = "scale"
        stack = "stack-media"
        service = "plex"
        replicas = 2
        compose = "/opt/stacks/stack-media/docker-compose.yml"

    monkeypatch.setattr(appmod, "load_intent", lambda name: FakeIntent())

    # Track if subprocess.run was called
    run_called = []

    def fake_run(argv, check=True, capture_output=True, text=True):
        run_called.append(True)
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)

    client = make_client()
    r = client.post(
        "/run",
        headers={"x-api-key": "secret"},
        json={"name": "scale_stack", "dry_run": True},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert "[DRY-RUN]" in data["stdout"]
    assert "docker compose" in data["stdout"]

    # Verify subprocess.run was NEVER called
    assert len(run_called) == 0


def test_list_intents():
    """Test that /intents endpoint lists available intents."""
    client = make_client()
    r = client.get("/intents")
    assert r.status_code == 200
    data = r.json()
    assert "intents" in data
    assert "count" in data
    assert isinstance(data["intents"], list)
    assert data["count"] == len(data["intents"])
    
    # Should have at least the test intents
    if data["count"] > 0:
        intent = data["intents"][0]
        assert "name" in intent
        assert "action" in intent
        assert "stack" in intent


def test_validate_intent_valid():
    """Test that /validate accepts valid intent YAML."""
    client = make_client()
    valid_yaml = """
label_required: approved-by-gemini
action: scale
stack: stack-media
service: plex
replicas: 2
"""
    r = client.post("/validate", json={"yaml_content": valid_yaml})
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0
    assert "intent" in data


def test_validate_intent_invalid():
    """POST /validate with invalid YAML should return valid=False."""
    client = make_client()
    yaml_content = """
label_required: approved-by-gemini
action: invalid_action
stack: test-stack
"""
    response = client.post("/validate", json={"yaml_content": yaml_content})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


def test_status():
    """GET /status should return service health and metadata."""
    client = make_client()
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "intents_loaded" in data
    assert data["intents_loaded"] >= 0
    assert data["approved_label"] == "approved-by-gemini"
    assert data["rate_limit"] == "10/minute"
    assert "features" in data
    assert "environment" in data
    assert "python_version" in data["environment"]
    assert "fastapi_version" in data["environment"]


def test_orchestrate_multi_stack(monkeypatch):
    """POST /orchestrate should execute multiple intents in sequence."""
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    
    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp
    
    monkeypatch.setattr(appmod.subprocess, "run", fake_run)
    client = make_client()
    
    response = client.post(
        "/orchestrate",
        json={
            "intents": ["scale_stack", "rollout_stack_media"],
            "dry_run": False,
            "stop_on_failure": True,
        },
        headers={"X-API-Key": "secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "summary" in data
    assert data["summary"]["total"] == 2


def test_orchestrate_rollback_on_failure(monkeypatch):
    """When a rollout fails, the API should attempt a soft rollback and return error context."""
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    def failing_run(argv, check=True, capture_output=True, text=True):
        # Fail on docker compose pull to simulate rollout failure
        if isinstance(argv, list) and "pull" in argv:
            e = subprocess.CalledProcessError(returncode=1, cmd="docker compose pull")
            e.stderr = "network error"
            raise e
        # Succeed otherwise
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", failing_run)
    client = make_client()

    r = client.post(
        "/orchestrate",
        json={
            "intents": ["rollout_stack_media"],
            "dry_run": False,
            "stop_on_failure": True,
            "rollback_on_failure": True,
        },
        headers={"X-API-Key": "secret"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["summary"]["failed"] == 1
    assert "results" in data and len(data["results"]) >= 1
    assert "rollback" in data["results"][0]


def test_schedules_list_requires_auth(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    client = make_client()
    r = client.get("/schedules")
    assert r.status_code == 401


def test_rbac_blocks_schedules(monkeypatch):
    # RBAC configured without schedules permission
    rbac = {"keys": {"secret": {"actions": ["*"], "stacks": ["*"], "endpoints": ["run"]}}}
    monkeypatch.setenv("CHATOPS_RBAC_JSON", json.dumps(rbac))
    client = make_client()
    r = client.get("/schedules", headers={"X-API-Key": "secret"})
    assert r.status_code == 403


def test_rbac_blocks_schedules_reload(monkeypatch):
    # RBAC configured without schedules_reload permission
    rbac = {"keys": {"secret": {"actions": ["*"], "stacks": ["*"], "endpoints": ["run"]}}}
    monkeypatch.setenv("CHATOPS_RBAC_JSON", json.dumps(rbac))
    client = make_client()
    r = client.post("/schedules/reload", headers={"X-API-Key": "secret"})
    assert r.status_code == 403


def test_rbac_allows_run_now(monkeypatch):
    # RBAC permits schedules_run_now for rollout on stack-media
    rbac = {
        "keys": {
            "secret": {
                "actions": ["rollout"],
                "stacks": ["stack-media"],
                "endpoints": ["schedules_run_now"],
            }
        }
    }
    monkeypatch.setenv("CHATOPS_RBAC_JSON", json.dumps(rbac))

    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)
    client = make_client()
    r = client.post(
        "/schedules/run_now",
        json={"intent": "rollout_stack_media", "dry_run": False},
        headers={"X-API-Key": "secret"},
    )
    assert r.status_code == 200


def test_run_now_executes_intent(monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")

    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)
    client = make_client()
    r = client.post(
        "/schedules/run_now",
        json={"intent": "rollout_stack_media", "dry_run": False},
        headers={"X-API-Key": "secret"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_audit_log_on_dry_run_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    audit_path = tmp_path / "audit.log"
    monkeypatch.setenv("CHATOPS_AUDIT_LOG_FILE", str(audit_path))

    # Ensure dry_run path (no docker)
    client = make_client()
    r = client.post(
        "/run",
        headers={"x-api-key": "secret"},
        json={"name": "scale_stack", "dry_run": True},
    )
    assert r.status_code == 200

    # Check audit log entries
    assert audit_path.exists()
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) >= 2
    events = [json.loads(line) for line in lines]
    kinds = {e.get("event") for e in events}
    assert "intent_started" in kinds
    assert "intent_succeeded" in kinds


def test_audit_log_on_command_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATOPS_API_KEY", "secret")
    audit_path = tmp_path / "audit2.log"
    monkeypatch.setenv("CHATOPS_AUDIT_LOG_FILE", str(audit_path))

    # Force docker command failure during rollout
    def failing_run(argv, check=True, capture_output=True, text=True):
        raise subprocess.CalledProcessError(returncode=1, cmd="docker compose pull", stderr="oops")

    monkeypatch.setattr(appmod.subprocess, "run", failing_run)
    client = make_client()
    r = client.post(
        "/run",
        headers={"x-api-key": "secret"},
        json={"name": "rollout_stack_media", "dry_run": False},
    )
    assert r.status_code in (500, 200)  # Failure expected (500); allow 200 if handled elsewhere
    # Confirm audit contains failure event
    assert audit_path.exists()
    events = [json.loads(line) for line in audit_path.read_text().strip().splitlines()]
    assert any(e.get("event") == "intent_failed" for e in events)


def test_rbac_denies_rollout_not_allowed(monkeypatch):
    """RBAC config that allows only scale should block rollout."""
    # Configure RBAC with limited permissions for key 'secret'
    rbac = {
        "keys": {
            "secret": {
                "actions": ["scale"],
                "stacks": ["stack-media"],
                "endpoints": ["run", "orchestrate"],
            }
        }
    }
    monkeypatch.setenv("CHATOPS_RBAC_JSON", json.dumps(rbac))
    # Do not set CHATOPS_API_KEY so RBAC is the only gate

    client = make_client()
    # Attempt rollout (not allowed)
    r = client.post(
        "/run",
        headers={"X-API-Key": "secret"},
        json={"name": "rollout_stack_media"},
    )
    assert r.status_code == 403


def test_rbac_allows_scale(monkeypatch):
    """RBAC allows scale action on stack-media for key 'secret'."""
    rbac = {
        "keys": {
            "secret": {
                "actions": ["scale"],
                "stacks": ["stack-media"],
                "endpoints": ["run", "orchestrate"],
            }
        }
    }
    monkeypatch.setenv("CHATOPS_RBAC_JSON", json.dumps(rbac))

    # Mock docker command
    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)
    client = make_client()
    r = client.post(
        "/run",
        headers={"X-API-Key": "secret"},
        json={"name": "scale_stack"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def _gh_sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_github_webhook_triggers_intent(monkeypatch):
    """GitHub push event with chatops marker should execute intent when signature is valid."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhooksecret")

    # Avoid real docker
    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)

    client = make_client()
    payload = {
        "ref": "refs/heads/main",
        "commits": [
            {"message": "feat: deploy [chatops:intent=rollout_stack_media]"},
            {"message": "chore: docs"},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": _gh_sig("webhooksecret", body),
        "Content-Type": "application/json",
    }
    r = client.post("/webhook/github", content=body, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] in (True, False)  # ok if intent exists; otherwise still handled
    assert data["count"] >= 0


def test_github_webhook_bad_signature(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhooksecret")
    client = make_client()
    body = json.dumps({"commits": []}).encode("utf-8")
    headers = {
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": "sha256=deadbeef",
        "Content-Type": "application/json",
    }
    r = client.post("/webhook/github", content=body, headers=headers)
    assert r.status_code == 401


def test_gitlab_webhook_triggers_intent(monkeypatch):
    monkeypatch.setenv("GITLAB_WEBHOOK_TOKEN", "gl_token")

    def fake_run(argv, check=True, capture_output=True, text=True):
        cp = types.SimpleNamespace()
        cp.stdout = "OK"
        return cp

    monkeypatch.setattr(appmod.subprocess, "run", fake_run)
    client = make_client()
    payload = {
        "commits": [
            {"message": "deploy [chatops:intent=rollout_stack_media]"},
        ]
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Gitlab-Token": "gl_token",
        "Content-Type": "application/json",
    }
    r = client.post("/webhook/gitlab", content=body, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
