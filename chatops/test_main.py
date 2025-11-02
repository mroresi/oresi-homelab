from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from chatops import main


client = TestClient(main.app)


def test_run_intent_success():
    fake_completed = MagicMock(stdout="done", returncode=0)
    with patch.object(main.subprocess, "run", return_value=fake_completed) as mock_run:
        response = client.post("/run", json={"name": "scale_stack"})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "stdout": "done"}
    mock_run.assert_called_once()


def test_run_intent_missing_file():
    response = client.post("/run", json={"name": "missing-intent"})
    assert response.status_code == 404


def test_run_intent_validation_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = {"label_required": "approved-by-gemini"}
    (tmp_path / "broken.yaml").write_text(yaml.safe_dump(data))
    monkeypatch.setattr(main, "INTENTS_DIR", tmp_path)

    response = client.post("/run", json={"name": "broken"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "command"
<<<<<<< ours
=======


def test_run_intent_invalid_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "bad.yaml").write_text("command: [unterminated")
    monkeypatch.setattr(main, "INTENTS_DIR", tmp_path)

    response = client.post("/run", json={"name": "bad"})

    assert response.status_code == 400
    assert "Invalid intent definition" in response.json()["detail"]


def test_run_intent_label_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "mismatch.yaml").write_text(
        yaml.safe_dump({
            "command": "echo hi",
            "label_required": "different-label",
        })
    )
    monkeypatch.setattr(main, "INTENTS_DIR", tmp_path)

    response = client.post("/run", json={"name": "mismatch"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Label requirement mismatch"
>>>>>>> theirs
