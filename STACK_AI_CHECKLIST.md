# Stack Checklist — AI

**Purpose**
Deploy AI-related containers (Ollama, OpenWebUI, Stable Diffusion).

**Pre-deploy Checks**
- GPU passthrough enabled on target node.
- Docker runtime supports CUDA.
- `/srv/ai_data` NFS mounted with correct permissions.

**Post-deploy Validation**
- Ollama responds at :11434 with model list.
- WebUI accessible on configured port.
- Disk utilization under 80%.

**Maintenance**
- Confirm weekly image pull + reload.
- Backup AI model configs in `/srv/backups/ai/`.
