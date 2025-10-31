from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml, os, subprocess

APPROVED_LABEL = os.getenv("APPROVED_LABEL","approved-by-gemini")

class IntentRequest(BaseModel):
    name: str

app = FastAPI()

def load_intent(name: str):
    path = os.path.join(os.path.dirname(__file__), "intents", f"{name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r") as f:
        return yaml.safe_load(f)

@app.post("/run")
def run_intent(req: IntentRequest):
    intent = load_intent(req.name)
    if intent.get("label_required", APPROVED_LABEL) != APPROVED_LABEL:
        raise HTTPException(403, "Label requirement mismatch")
    cmd = intent.get("command")
    if not cmd:
        raise HTTPException(400, "No command in intent")
    try:
        res = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return {"ok": True, "stdout": res.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Command failed: {e.stderr}")
