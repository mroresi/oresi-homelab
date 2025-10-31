import hashlib
import hmac
import importlib
import ipaddress
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any, List, Literal, Optional, cast

# Optional APScheduler import (lazy to avoid unresolved import errors when not installed)
try:
    import importlib.util as _importlib_util
    HAVE_APSCHEDULER = _importlib_util.find_spec("apscheduler") is not None
except Exception:
    HAVE_APSCHEDULER = False

# Type stubs for optional APScheduler classes
if TYPE_CHECKING:
    # Only needed for type checking, not at runtime
    try:
        from apscheduler.schedulers.background import (
            BackgroundScheduler as _BackgroundSchedulerType,
        )
        from apscheduler.triggers.cron import (
            CronTrigger as _CronTriggerType,
        )
    except Exception:  # pragma: no cover - typing-time only
        _BackgroundSchedulerType = Any
        _CronTriggerType = Any
else:
    _BackgroundSchedulerType = object
    _CronTriggerType = object

import httpx
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .logging_setup import setup_logging

VERSION = "1.0.0"
SERVICE_START_TIME = time.time()
STATE_DIR = os.getenv(
    "CHATOPS_STATE_DIR",
    os.path.join(os.path.dirname(__file__), ".state"),
)
SCHEDULES_FILE = os.getenv(
    "CHATOPS_SCHEDULES_FILE",
    os.path.join(os.path.dirname(__file__), "schedules.json"),
)
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() in {"1", "true", "yes"}
AUDIT_LOG_FILE = os.getenv(
    "CHATOPS_AUDIT_LOG_FILE",
    os.path.join(os.path.dirname(__file__), ".state", "audit.log"),
)

def _apscheduler_classes():
    """Lazily import APScheduler classes when available/enabled."""
    if not HAVE_APSCHEDULER:
        raise RuntimeError("APScheduler not installed")
    sched_mod = importlib.import_module("apscheduler.schedulers.background")
    trig_mod = importlib.import_module("apscheduler.triggers.cron")
    return sched_mod.BackgroundScheduler, trig_mod.CronTrigger

APPROVED_LABEL = os.getenv("APPROVED_LABEL", "approved-by-gemini")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

setup_logging()

# Rate limiter: 10 requests per minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

# Prometheus metrics
INTENT_REQUESTS = Counter(
    "chatops_intent_requests_total",
    "Total intent execution requests",
    ["intent_name", "action", "stack", "dry_run"],
)
INTENT_FAILURES = Counter(
    "chatops_intent_failures_total",
    "Failed intent executions",
    ["intent_name", "action", "stack", "reason"],
)
INTENT_DURATION = Histogram(
    "chatops_intent_duration_seconds",
    "Intent execution duration",
    ["intent_name", "action"],
)
AUTH_FAILURES = Counter(
    "chatops_auth_failures_total", "Authentication failures", ["reason"]
)


def _audit_write_line(line: str) -> None:
    try:
        path = os.getenv("CHATOPS_AUDIT_LOG_FILE", AUDIT_LOG_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        logging.debug("audit_write_failed: %s", e)


def audit_log(event: dict) -> None:
    """Write a single JSON line audit event. Best-effort, never raises."""
    try:
        payload = {
            "ts": int(time.time()),
            **event,
        }
        _audit_write_line(json.dumps(payload, separators=(",", ":")))
    except Exception as e:
        logging.debug("audit_log_failed: %s", e)



def send_discord_alert(message: str, color: int = 0x00FF00) -> None:
    """Send audit alert to Discord webhook (non-blocking, best-effort)."""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        payload = {
            "embeds": [
                {
                    "title": "ChatOps Audit",
                    "description": message,
                    "color": color,
                    "timestamp": None,  # Discord will use current time
                }
            ]
        }
        httpx.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5.0)
    except Exception as e:
        logging.warning("Failed to send Discord alert: %s", e)


class IntentRequest(BaseModel):
    name: str
    dry_run: bool = False  # Preview mode: show what would be executed without running
    rollback_on_failure: bool = True  # Attempt rollback if execution fails


class MultiStackRequest(BaseModel):
    """Execute multiple intents in sequence."""
    intents: List[str]  # List of intent names to execute
    dry_run: bool = False
    stop_on_failure: bool = True  # Stop execution if any intent fails
    rollback_on_failure: bool = True


class Intent(BaseModel):
    # Minimal structured intent schema
    label_required: str = APPROVED_LABEL
    action: Literal["scale", "rollout"]  # TODO: Add "backup" action support
    stack: str
    service: Optional[str] = None
    replicas: Optional[int] = None
    compose: Optional[str] = None  # override compose file path if needed
    depends_on: Optional[List[str]] = None  # Intent dependencies (execute these first)


def _ensure_state_dir() -> None:
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except Exception as e:
        logging.warning("Failed to create state dir %s: %s", STATE_DIR, e)


def _state_path() -> str:
    return os.path.join(STATE_DIR, "state.json")


def _state_read() -> dict:
    try:
        _ensure_state_dir()
        path = _state_path()
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.warning("Failed to read state: %s", e)
        return {}


def _state_write(data: dict) -> None:
    try:
        _ensure_state_dir()
        tmp_path = _state_path() + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, _state_path())
    except Exception as e:
        logging.warning("Failed to write state: %s", e)


def _record_scale_transition(stack: str, service: str, new_replicas: int) -> None:
    state = _state_read()
    scale_state = state.setdefault("scale", {})
    stack_state = scale_state.setdefault(stack, {})
    svc_state = stack_state.setdefault(service, {})
    # Shift last desired to previous, update last desired
    prev = svc_state.get("last_desired")
    if prev is not None:
        svc_state["previous_desired"] = prev
    svc_state["last_desired"] = new_replicas
    svc_state["updated_at"] = int(time.time())
    _state_write(state)


def _get_previous_desired(stack: str, service: str) -> Optional[int]:
    state = _state_read()
    try:
        return state["scale"][stack][service].get("previous_desired")
    except Exception:
        return None


def _attempt_rollback(intent: Intent, request: Request) -> Optional[str]:
    """Best-effort rollback for supported actions. Returns message or None."""
    try:
        compose_file = intent.compose or f"/opt/stacks/{intent.stack}/docker-compose.yml"
        if intent.action == "scale":
            if not intent.service:
                return "No service specified for scale rollback"
            prev = _get_previous_desired(intent.stack, intent.service)
            if prev is None:
                return "No previous desired replicas to rollback to"
            argv = [
                "docker",
                "compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "--scale",
                f"{intent.service}={prev}",
            ]
            res = subprocess.run(argv, check=True, capture_output=True, text=True)
            logging.info(
                "rollback_scale",
                extra={
                    "stack": intent.stack,
                    "service": intent.service,
                    "replicas": prev,
                    "stdout": res.stdout,
                },
            )
            audit_log({
                "event": "intent_rollback",
                "action": "scale",
                "stack": intent.stack,
                "service": intent.service,
                "replicas": prev,
                "ok": True,
            })
            return "Scaled back to previous desired replicas"
        elif intent.action == "rollout":
            # Soft rollback: restart without pulling latest
            argv = ["docker", "compose", "-f", compose_file, "up", "-d"]
            res = subprocess.run(argv, check=True, capture_output=True, text=True)
            logging.info(
                "rollback_rollout_restart",
                extra={"stack": intent.stack, "stdout": res.stdout},
            )
            audit_log({
                "event": "intent_rollback",
                "action": "rollout",
                "stack": intent.stack,
                "ok": True,
            })
            return "Restarted services (soft rollback)"
    except subprocess.CalledProcessError as e:
        logging.error(
            "rollback_failed",
            extra={"rc": e.returncode, "stderr": e.stderr},
        )
        audit_log({
            "event": "intent_rollback",
            "ok": False,
            "error": "command_failed",
            "stderr": (e.stderr or "")[:200],
            "action": intent.action,
            "stack": intent.stack,
            "service": intent.service,
        })
        return f"Rollback failed: {e.stderr[:200]}"
    except Exception as e:
        logging.error("rollback_error: %s", e)
        audit_log({
            "event": "intent_rollback",
            "ok": False,
            "error": str(e),
            "action": intent.action,
            "stack": intent.stack,
            "service": intent.service,
        })
        return f"Rollback error: {e}"


app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler)
)

# Scheduler state
app.state.scheduler = None
app.state.schedules_loaded = []


def _scheduler_load_jobs(app: FastAPI) -> None:
    app.state.schedules_loaded = []
    if not (ENABLE_SCHEDULER and HAVE_APSCHEDULER):
        return
    if not os.path.exists(SCHEDULES_FILE):
        return
    try:
        with open(SCHEDULES_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        logging.warning("Failed to load schedules file: %s", e)
        return
    # Data format: {"schedules": [{name, intent, cron, interval_seconds, dry_run, enabled}]}
    schedules = data.get("schedules", [])
    for s in schedules:
        if not s.get("enabled", False):
            continue
        name = s.get("name")
        intent_name = s.get("intent")
        dry_run = bool(s.get("dry_run", False))
        if not name or not intent_name:
            continue
        def _job_runner(intent_name=intent_name, dry_run=dry_run):  # bind defaults
            try:
                intent = load_intent(intent_name)
                req = IntentRequest(name=intent_name, dry_run=dry_run)
                _execute_single_intent(req, Request(scope={"type": "http"}), intent)
                logging.info("schedule_run", extra={"intent": intent_name, "dry_run": dry_run})
            except Exception as e:
                logging.error("schedule_run_failed", extra={"intent": intent_name, "error": str(e)})
        if s.get("cron"):
            try:
                # Lazily import CronTrigger only when needed
                _, CronTrigger = _apscheduler_classes()
                trigger = CronTrigger.from_crontab(s["cron"])
                app.state.scheduler.add_job(
                    _job_runner, trigger, id=name, replace_existing=True
                )
                app.state.schedules_loaded.append(
                    {
                        "name": name,
                        "intent": intent_name,
                        "type": "cron",
                        "cron": s["cron"],
                        "dry_run": dry_run,
                    }
                )
            except Exception as e:
                logging.warning("Invalid cron schedule %s: %s", name, e)
        elif s.get("interval_seconds"):
            seconds = int(s["interval_seconds"])  
            app.state.scheduler.add_job(
                _job_runner, "interval", seconds=seconds, id=name, replace_existing=True
            )
            app.state.schedules_loaded.append(
                {
                    "name": name,
                    "intent": intent_name,
                    "type": "interval",
                    "seconds": seconds,
                    "dry_run": dry_run,
                }
            )


@app.on_event("startup")
def _startup_scheduler() -> None:
    if ENABLE_SCHEDULER and HAVE_APSCHEDULER:
        try:
            # Lazily import BackgroundScheduler only when needed
            BackgroundScheduler, _ = _apscheduler_classes()
            app.state.scheduler = BackgroundScheduler()
            app.state.scheduler.start()
            _scheduler_load_jobs(app)
            logging.info("scheduler_started", extra={"schedules": len(app.state.schedules_loaded)})
        except Exception as e:
            logging.warning("Failed to start scheduler: %s", e)
    else:
        logging.info(
            "scheduler_disabled",
            extra={"enabled": ENABLE_SCHEDULER, "have_lib": HAVE_APSCHEDULER},
        )


def load_intent(name: str) -> Intent:
    path = os.path.join(os.path.dirname(__file__), "intents", f"{name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    try:
        return Intent(**raw)
    except Exception as e:
        logging.error("Intent validation failed for %s: %s", name, e)
        raise


def get_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    required = os.getenv("CHATOPS_API_KEY")
    # Accept either global API key or RBAC-defined key when RBAC is configured
    rbac = _rbac_config()
    valid = False
    if rbac:
        valid = bool(x_api_key) and x_api_key in rbac.get("keys", {})
    if not valid and required:
        valid = bool(x_api_key) and secrets.compare_digest(x_api_key, required)
    if not valid:
        # If neither RBAC nor global key is configured, return 503
        if not rbac and not required:
            logging.warning("No API key configured (CHATOPS_API_KEY) and RBAC not set")
            raise HTTPException(503, "Server not configured with API key")
        AUTH_FAILURES.labels(reason="invalid_key").inc()
        send_discord_alert("🚨 **AUTH FAILED**: Invalid API key attempt", color=0xFF0000)
        raise HTTPException(401, "Unauthorized")
    return x_api_key or ""


def _rbac_config() -> Optional[dict]:
    """Load RBAC configuration from env JSON or file.
    Caches but refreshes when environment values change (safe for tests).
    """
    if not hasattr(_rbac_config, "_cache_data"):
        _rbac_config._cache_data = None  # type: ignore[attr-defined]
        _rbac_config._cache_key = ("", "", 0.0)  # type: ignore[attr-defined]

    cfg_json = os.getenv("CHATOPS_RBAC_JSON", "").strip()
    cfg_file = os.getenv("CHATOPS_RBAC_FILE", "").strip()
    file_mtime = 0.0
    if cfg_file and os.path.exists(cfg_file):
        try:
            file_mtime = os.path.getmtime(cfg_file)
        except OSError:
            file_mtime = 0.0

    key = (cfg_json, cfg_file, file_mtime)
    # Safe attribute access with type ignore for dynamic attributes
    if _rbac_config._cache_key == key:  # type: ignore[attr-defined]
        return _rbac_config._cache_data  # type: ignore[attr-defined]

    data: Optional[dict] = None
    try:
        if cfg_json:
            data = json.loads(cfg_json)
        elif cfg_file and os.path.exists(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as e:
        logging.warning("Failed to load RBAC config: %s", e)
        data = None

    _rbac_config._cache_key = key  # type: ignore[attr-defined]
    _rbac_config._cache_data = data  # type: ignore[attr-defined]
    return data


def _rbac_allowed(api_key: str, endpoint: str, action: Optional[str], stack: Optional[str]) -> bool:
    cfg = _rbac_config()
    if not cfg:
        return True  # No RBAC configured → allow
    keys = cfg.get("keys", {})
    entry = keys.get(api_key)
    if not entry:
        return False
    # Endpoints
    allowed_endpoints = entry.get("endpoints")
    if allowed_endpoints and endpoint not in allowed_endpoints and "*" not in allowed_endpoints:
        return False
    # Actions
    if action is not None:
        allowed_actions = entry.get("actions")
        if allowed_actions and action not in allowed_actions and "*" not in allowed_actions:
            return False
    # Stacks
    if stack is not None:
        allowed_stacks = entry.get("stacks")
        if allowed_stacks and stack not in allowed_stacks and "*" not in allowed_stacks:
            return False
    return True


def get_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For first value if present, else use client host
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def check_client_allowed(request: Request) -> None:
    allow = os.getenv("CHATOPS_IP_ALLOWLIST", "").strip()
    if not allow:
        return  # no restriction
    client = get_client_ip(request)
    if allow == "*":
        return
    # Allow comma-separated tokens; support CIDR, exact IP, or exact host string
    tokens = [t.strip() for t in allow.split(",") if t.strip()]
    for t in tokens:
        try:
            # CIDR or IP match
            if "/" in t:
                net = ipaddress.ip_network(t, strict=False)
                ip = ipaddress.ip_address(client)
                if ip in net:
                    return
            else:
                # exact IP literal
                ip = ipaddress.ip_address(t)
                if client == str(ip):
                    return
        except ValueError:
            # Not an IP/CIDR → allow exact host string match
            if client == t:
                return
    send_discord_alert(
        f"🚨 **IP BLOCKED**: Client `{client}` not in allowlist", color=0xFF0000
    )
    raise HTTPException(403, "Client IP not allowed")
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
@limiter.exempt  # Don't rate-limit metrics scraping
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.get("/status")
def status():
    """Service status and health information."""
    uptime_seconds = time.time() - SERVICE_START_TIME
    
    # Count loaded intents
    intents_dir = os.path.join(os.path.dirname(__file__), "intents")
    intent_count = 0
    if os.path.exists(intents_dir):
        intent_count = len([
            f for f in os.listdir(intents_dir)
            if f.endswith(".yaml")
        ])
    
    return {
        "status": "healthy",
        "version": VERSION,
        "uptime_seconds": int(uptime_seconds),
        "intents_loaded": intent_count,
        "approved_label": APPROVED_LABEL,
        "rate_limit": "10/minute",
        "features": {
            "dry_run": True,
            "prometheus_metrics": True,
            "discord_alerts": bool(DISCORD_WEBHOOK_URL),
            "ip_allowlist": bool(os.getenv("CHATOPS_IP_ALLOWLIST")),
        },
        "environment": {
            "python_version": (
                f"{sys.version_info.major}.{sys.version_info.minor}"
                f".{sys.version_info.micro}"
            ),
            "fastapi_version": "0.115.5",
        }
    }


@app.get("/intents")
def list_intents():
    """List all available intents with metadata."""
    intents_dir = os.path.join(os.path.dirname(__file__), "intents")
    if not os.path.exists(intents_dir):
        return {"intents": []}
    
    intents = []
    for yaml_file in sorted(os.listdir(intents_dir)):
        if not yaml_file.endswith(".yaml"):
            continue
        
        try:
            intent_name = yaml_file[:-5]  # Remove .yaml extension
            intent = load_intent(intent_name)
            
            # Extract description from YAML comment if present
            yaml_path = os.path.join(intents_dir, yaml_file)
            description = None
            with open(yaml_path) as f:
                first_line = f.readline().strip()
                if first_line.startswith("#"):
                    description = first_line[1:].strip()
            
            intents.append({
                "name": intent_name,
                "action": intent.action,
                "stack": intent.stack,
                "service": intent.service,
                "description": description,
                "label_required": intent.label_required,
            })
        except Exception as e:
            logging.warning("Failed to load intent %s: %s", yaml_file, e)
            continue
    
    return {"intents": intents, "count": len(intents)}


class ValidateRequest(BaseModel):
    """Request to validate intent YAML."""
    yaml_content: str


@app.post("/validate")
def validate_intent(req: ValidateRequest):
    """Validate intent YAML without executing it."""
    try:
        # Parse YAML
        raw = yaml.safe_load(req.yaml_content)
        if not raw:
            return {
                "valid": False,
                "errors": ["Empty YAML content"],
            }
        
        # Validate against Intent schema
        intent = Intent(**raw)
        
        # Additional validation
        errors = []
        warnings = []
        
        if intent.action == "scale":
            if not intent.service:
                errors.append("action=scale requires 'service' field")
            if intent.replicas is None:
                errors.append("action=scale requires 'replicas' field")
        
        if intent.label_required != APPROVED_LABEL:
            warnings.append(
                f"label_required '{intent.label_required}' differs from server "
                f"expectation '{APPROVED_LABEL}'"
            )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "intent": {
                "action": intent.action,
                "stack": intent.stack,
                "service": intent.service,
                "replicas": intent.replicas,
                "label_required": intent.label_required,
            },
        }
    
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "errors": [f"YAML parsing error: {str(e)}"],
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
        }


class RunNowRequest(BaseModel):
    """Trigger an immediate run of an intent (bypasses scheduler)."""
    intent: str
    dry_run: bool = False


@app.get("/schedules")
def list_schedules(
    request: Request,
    _: str = Depends(get_api_key),
    __: None = Depends(check_client_allowed),
):
    api_key = request.headers.get("x-api-key", "")
    if not _rbac_allowed(api_key, endpoint="schedules", action=None, stack=None):
        raise HTTPException(403, "RBAC: schedules not permitted")
    return {
        "enabled": ENABLE_SCHEDULER,
        "have_apscheduler": HAVE_APSCHEDULER,
        "loaded": app.state.schedules_loaded,
        "count": len(app.state.schedules_loaded),
    }


@app.post("/schedules/reload")
def reload_schedules(
    request: Request,
    _: str = Depends(get_api_key),
    __: None = Depends(check_client_allowed),
):
    api_key = request.headers.get("x-api-key", "")
    if not _rbac_allowed(api_key, endpoint="schedules_reload", action=None, stack=None):
        raise HTTPException(403, "RBAC: schedules reload not permitted")
    if not (ENABLE_SCHEDULER and HAVE_APSCHEDULER and app.state.scheduler):
        return {"ok": False, "error": "Scheduler not enabled"}
    try:
        _scheduler_load_jobs(app)
        return {"ok": True, "count": len(app.state.schedules_loaded)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/schedules/run_now")
def run_now(
    req: RunNowRequest,
    request: Request,
    _: str = Depends(get_api_key),
    __: None = Depends(check_client_allowed),
):
    intent = load_intent(req.intent)
    api_key = request.headers.get("x-api-key", "")
    if not _rbac_allowed(
        api_key,
        endpoint="schedules_run_now",
        action=intent.action,
        stack=intent.stack,
    ):
        raise HTTPException(403, "RBAC: run_now not permitted for intent")
    result = _execute_single_intent(
        IntentRequest(name=req.intent, dry_run=req.dry_run), request, intent
    )
    return result


@app.post("/orchestrate")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
def orchestrate_multi_stack(
    req: MultiStackRequest,
    request: Request,
    _: str = Depends(get_api_key),
    __: None = Depends(check_client_allowed),
):
    """Execute multiple intents in sequence with dependency resolution."""
    results = []
    executed = set()
    
    def resolve_and_execute(intent_name: str, depth: int = 0) -> dict:
        """Recursively execute intent with dependency resolution."""
        if depth > 10:
            raise HTTPException(500, f"Dependency depth too deep for {intent_name}")
        
        if intent_name in executed:
            return {"skipped": True, "reason": "already_executed"}
        
        # Load intent
        try:
            intent = load_intent(intent_name)
        except FileNotFoundError:
            return {
                "intent": intent_name,
                "ok": False,
                "error": f"Intent not found: {intent_name}",
            }
        
        # Execute dependencies first
        if intent.depends_on:
            for dep in intent.depends_on:
                dep_result = resolve_and_execute(dep, depth + 1)
                if not dep_result.get("ok", False) and not dep_result.get("skipped", False):
                    if req.stop_on_failure:
                        return {
                            "intent": intent_name,
                            "ok": False,
                            "error": f"Dependency failed: {dep}",
                            "dependency_result": dep_result,
                        }
        
        # Execute this intent
        executed.add(intent_name)
        
        # Create IntentRequest and execute via run_intent logic
        intent_req = IntentRequest(name=intent_name, dry_run=req.dry_run)
        
        try:
            # Reuse execution logic
            api_key = request.headers.get("x-api-key", "")
            if not _rbac_allowed(
                api_key,
                endpoint="orchestrate",
                action=intent.action,
                stack=intent.stack,
            ):
                return {
                    "intent": intent_name,
                    "ok": False,
                    "error": "RBAC: action not permitted",
                }
            result = _execute_single_intent(intent_req, request, intent)
            return {
                "intent": intent_name,
                "ok": result.get("ok", False),
                "action": intent.action,
                "stack": intent.stack,
                "dry_run": req.dry_run,
                "stdout": result.get("stdout", ""),
            }
        except Exception as e:
            rollback_msg = None
            if req.rollback_on_failure and not req.dry_run:
                rollback_msg = _attempt_rollback(intent, request)
            return {
                "intent": intent_name,
                "ok": False,
                "error": str(e),
                "rollback": rollback_msg,
            }
    
    # Execute all requested intents
    for intent_name in req.intents:
        result = resolve_and_execute(intent_name)
        results.append(result)
        
        if not result.get("ok", False) and req.stop_on_failure:
            send_discord_alert(
                f"❌ **ORCHESTRATION FAILED**: Stopped at intent `{intent_name}`",
                color=0xFF0000,
            )
            break
    
    success_count = sum(1 for r in results if r.get("ok", False))
    total_count = len(results)
    
    if success_count == total_count:
        send_discord_alert(
            f"✅ **ORCHESTRATION SUCCESS**: {success_count}/{total_count} intents completed",
            color=0x00FF00,
        )
    
    return {
        "ok": success_count == total_count,
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "failed": total_count - success_count,
        },
    }


def _execute_single_intent(req: IntentRequest, request: Request, intent: Intent) -> dict:
    """Extracted single intent execution logic."""
    # Track request
    INTENT_REQUESTS.labels(
        intent_name=req.name,
        action=intent.action,
        stack=intent.stack,
        dry_run=str(req.dry_run),
    ).inc()
    # Audit: started
    audit_log({
        "event": "intent_started",
        "intent": req.name,
        "action": intent.action,
        "stack": intent.stack,
        "service": intent.service,
        "replicas": intent.replicas,
        "dry_run": req.dry_run,
    })
    
    if intent.label_required != APPROVED_LABEL:
        INTENT_FAILURES.labels(
            intent_name=req.name,
            action=intent.action,
            stack=intent.stack,
            reason="label_mismatch",
        ).inc()
        audit_log({
            "event": "intent_denied",
            "intent": req.name,
            "action": intent.action,
            "stack": intent.stack,
            "reason": "label_mismatch",
        })
        raise HTTPException(403, "Label requirement mismatch")

    compose_file = intent.compose or f"/opt/stacks/{intent.stack}/docker-compose.yml"

    def run_argv(argv: List[str]):
        client_host = request.client.host if request.client else None
        
        if req.dry_run:
            logging.info(
                "dry_run_preview",
                extra={
                    "intent": req.name,
                    "action": intent.action,
                    "stack": intent.stack,
                    "service": intent.service,
                    "replicas": intent.replicas,
                    "argv": argv,
                    "client": client_host,
                    "dry_run": True,
                },
            )
            return f"[DRY-RUN] Would execute: {' '.join(argv)}"
        
        logging.info(
            "executing",
            extra={
                "intent": req.name,
                "action": intent.action,
                "stack": intent.stack,
                "service": intent.service,
                "replicas": intent.replicas,
                "argv": argv,
                "client": client_host,
            },
        )
        try:
            with INTENT_DURATION.labels(intent_name=req.name, action=intent.action).time():
                res = subprocess.run(argv, check=True, capture_output=True, text=True)
            return res.stdout
        except subprocess.CalledProcessError as e:
            INTENT_FAILURES.labels(
                intent_name=req.name,
                action=intent.action,
                stack=intent.stack,
                reason="command_failed",
            ).inc()
            logging.error(
                "command_failed",
                extra={
                    "rc": e.returncode,
                    "stderr": e.stderr,
                    "intent": req.name,
                    "argv": argv,
                },
            )
            audit_log({
                "event": "intent_failed",
                "intent": req.name,
                "action": intent.action,
                "stack": intent.stack,
                "stderr": (e.stderr or "")[:200],
            })
            raise HTTPException(500, f"Command failed: {e.stderr}") from e

    if intent.action == "scale":
        if not intent.service or intent.replicas is None:
            audit_log({
                "event": "intent_invalid",
                "intent": req.name,
                "action": intent.action,
                "stack": intent.stack,
                "reason": "missing_fields",
            })
            raise HTTPException(400, "Missing service or replicas for scale action")
        # Record transition for potential rollback
        try:
            _record_scale_transition(intent.stack, intent.service, int(intent.replicas))
        except Exception as e:
            logging.warning("Failed recording scale transition: %s", e)
        argv = [
            "docker",
            "compose",
            "-f",
            compose_file,
            "up",
            "-d",
            "--scale",
            f"{intent.service}={intent.replicas}",
        ]
        out = run_argv(argv)
        result = {
            "ok": True,
            "dry_run": req.dry_run,
            "stdout": out,
            "intent": req.name,
            "action": intent.action,
        }
        audit_log({
            "event": "intent_succeeded",
            "intent": req.name,
            "action": intent.action,
            "stack": intent.stack,
            "service": intent.service,
            "replicas": intent.replicas,
            "dry_run": req.dry_run,
        })
        return result
    elif intent.action == "rollout":
        out1 = run_argv(["docker", "compose", "-f", compose_file, "pull"])
        out2 = run_argv(["docker", "compose", "-f", compose_file, "up", "-d"])
        result = {
            "ok": True,
            "dry_run": req.dry_run,
            "stdout": out1 + out2,
            "intent": req.name,
            "action": intent.action,
        }
        audit_log({
            "event": "intent_succeeded",
            "intent": req.name,
            "action": intent.action,
            "stack": intent.stack,
            "dry_run": req.dry_run,
        })
        return result
    else:
        raise HTTPException(400, "Unsupported action")


@app.post("/run")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
def run_intent(
    req: IntentRequest,
    request: Request,
    _: str = Depends(get_api_key),
    __: None = Depends(check_client_allowed),
):
    """Execute a single intent."""
    intent = load_intent(req.name)
    # RBAC enforcement (optional)
    # Accept standard header casing; Starlette lowercases header keys
    api_key = request.headers.get("x-api-key", "")
    if not _rbac_allowed(api_key, endpoint="run", action=intent.action, stack=intent.stack):
        raise HTTPException(403, "RBAC: action not permitted")
    try:
        result = _execute_single_intent(req, request, intent)
        send_discord_alert(
            f"✅ **SUCCESS**: `{intent.action}` on stack `{intent.stack}` "
            f"(intent: `{req.name}`)",
            color=0x00FF00,
        )
        return result
    except Exception as e:
        rollback_msg = None
        if req.rollback_on_failure and not req.dry_run:
            rollback_msg = _attempt_rollback(intent, request)
        audit_log({
            "event": "intent_exception",
            "intent": req.name,
            "action": intent.action,
            "stack": intent.stack,
            "service": intent.service,
            "dry_run": req.dry_run,
            "error": str(e),
            "rollback": rollback_msg,
        })
        if not isinstance(e, HTTPException):
            send_discord_alert(
                f"❌ **INTENT FAILED**: `{intent.action}` on `{intent.stack}`",
                color=0xFF0000,
            )
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(500, str(e)) from e


def _extract_intents_from_commits(commits: list[dict]) -> list[str]:
    intents: list[str] = []
    pattern = re.compile(r"\[chatops:intent=([^\]]+)\]")
    for c in commits or []:
        msg = c.get("message", "")
        for m in pattern.finditer(msg):
            intents.append(m.group(1))
    return intents


@app.post("/webhook/github")
async def github_webhook(request: Request):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    sig = request.headers.get("x-hub-signature-256", "")
    body = await request.body()
    if not secret:
        raise HTTPException(401, "Webhook secret not configured")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not secrets.compare_digest(expected, sig):
        raise HTTPException(401, "Invalid signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, "Invalid JSON payload") from e
    commits = payload.get("commits", [])
    intents = _extract_intents_from_commits(commits)
    return {"ok": True, "count": len(intents), "intents": intents}


@app.post("/webhook/gitlab")
async def gitlab_webhook(request: Request):
    token = os.getenv("GITLAB_WEBHOOK_TOKEN", "")
    header = request.headers.get("x-gitlab-token", "")
    if not token:
        raise HTTPException(401, "Webhook token not configured")
    if not secrets.compare_digest(token, header):
        raise HTTPException(401, "Invalid token")
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, "Invalid JSON payload") from e
    commits = payload.get("commits", [])
    intents = _extract_intents_from_commits(commits)
    return {"ok": True, "results": intents}
