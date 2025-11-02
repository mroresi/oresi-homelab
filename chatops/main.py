import os
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
<<<<<<< ours
from pydantic import BaseModel, ValidationError
=======
from pydantic import BaseModel, ValidationError, constr
>>>>>>> theirs

APPROVED_LABEL = os.getenv("APPROVED_LABEL", "approved-by-gemini")
INTENTS_DIR = Path(__file__).resolve().parent / "intents"


class IntentRequest(BaseModel):
    name: str


class IntentConfig(BaseModel):
<<<<<<< ours
    command: str
=======
    command: constr(strip_whitespace=True, min_length=1)  # type: ignore[valid-type]
>>>>>>> theirs
    label_required: Optional[str] = None
    working_directory: Optional[str] = None


app = FastAPI()


def load_intent(name: str) -> IntentConfig:
    """Load an intent definition from disk."""

    path = INTENTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Intent '{name}' was not found")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid intent definition: {exc}") from exc
    try:
        return IntentConfig(**data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@app.post("/run")
def run_intent(req: IntentRequest):
    intent = load_intent(req.name)
<<<<<<< ours
    if (intent.label_required or APPROVED_LABEL) != APPROVED_LABEL:
=======
    if intent.label_required and intent.label_required != APPROVED_LABEL:
>>>>>>> theirs
        raise HTTPException(status_code=403, detail="Label requirement mismatch")

    try:
        res = subprocess.run(
            intent.command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=intent.working_directory,
        )
        return {"ok": True, "stdout": res.stdout}
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Command failed",
                "returncode": exc.returncode,
                "stderr": exc.stderr,
            },
        ) from exc
