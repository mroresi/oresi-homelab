# Stack AI — Ollama, OpenWebUI & Stable Diffusion

## Overview

This stack deploys AI inference services with GPU acceleration for local LLM and image generation.

## Services

| Service | Port | Purpose | GPU Required |
|---------|------|---------|--------------|
| **Ollama** | 11434 | LLM inference engine | Yes |
| **OpenWebUI** | 3000 | Web interface for LLMs | No |
| **Stable Diffusion** | 7860 | Image generation WebUI | Yes |

## Prerequisites

### Hardware
- NVIDIA GPU with CUDA support
- Minimum 8GB VRAM (16GB recommended)
- GPU passthrough enabled on Proxmox node

### Software
- Docker with NVIDIA runtime support
- `nvidia-container-toolkit` installed
- NFS mount at `/srv/ai_data` with proper permissions

### Verify GPU Support
```bash
# Check NVIDIA driver
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## Deployment

### Via ChatOps (Recommended)
```bash
# Rollout/update the stack
curl -X POST https://whitebox.bombay-porgy.ts.net:8000/run \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "rollout_stack_ai"}'

# Scale Ollama for increased load
curl -X POST https://whitebox.bombay-porgy.ts.net:8000/run \
  -H "X-API-Key: $CHATOPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "scale_stack_ai"}'
```

### Manual Deployment
```bash
cd /opt/stacks/stack-ai
docker-compose pull
docker-compose up -d
```

## Post-Deployment Validation

### Check Service Health
```bash
# Ollama API
curl http://localhost:11434/api/tags

# OpenWebUI (from host)
curl http://localhost:3000/health

# OpenWebUI (from inside the container)
docker exec openwebui curl http://localhost:8080/health

# Stable Diffusion
curl http://localhost:7860/
```

### Verify GPU Usage
```bash
# Watch GPU utilization during inference
watch -n 1 nvidia-smi
```

### Test Model Inference
```bash
# Pull a model (first time)
docker exec ollama ollama pull llama2

# Test inference
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Why is the sky blue?"
}'
```

## Configuration

### Environment Variables
Create a `.env` file in this directory:
```env
# OpenWebUI
WEBUI_SECRET_KEY=your-secret-key-here
WEBUI_AUTH=true

# Optional: Custom models path
OLLAMA_MODELS=/srv/ai_data/ollama/models
```

### Volume Mounts
All persistent data is stored under `/srv/ai_data/`:
- `/srv/ai_data/ollama` — Ollama models and config
- `/srv/ai_data/openwebui` — OpenWebUI database and user data
- `/srv/ai_data/stable-diffusion/models` — SD models
- `/srv/ai_data/stable-diffusion/outputs` — Generated images

### GPU Allocation
To specify GPU device IDs:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ['0']  # Use first GPU only
          capabilities: [gpu]
```

## Maintenance

### Update Services
```bash
docker-compose pull
docker-compose up -d
```

### Backup Models
```bash
# Backup to Synology
rsync -avz /srv/ai_data/ollama/ /srv/backups/ai/ollama/
rsync -avz /srv/ai_data/stable-diffusion/models/ /srv/backups/ai/sd-models/
```

### Cleanup Old Models
```bash
# List installed models
docker exec ollama ollama list

# Remove unused model
docker exec ollama ollama rm <model-name>
```

### Monitor Disk Usage
```bash
# Check AI data volume
df -h /srv/ai_data

# Find large files
du -sh /srv/ai_data/*
```

## Troubleshooting

### GPU Not Detected
```bash
# Verify NVIDIA runtime
docker info | grep -i runtime

# Check container can access GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory Errors
- Check available VRAM: `nvidia-smi`
- Reduce concurrent model instances
- Use smaller/quantized models
- Configure model offloading in Ollama

### Slow Model Loading
- Models are loaded on first inference
- Large models (70B+) may take 1-2 minutes
- Check health logs: `docker-compose logs -f ollama`

### Port Conflicts
If ports are already in use, modify in `docker-compose.yml`:
```yaml
ports:
  - "11434:11434"  # Change first number to available port
```

## Monitoring

### Grafana Dashboards
- **NVIDIA GPU Metrics** — Real-time VRAM, temperature, utilization
- **Ollama Performance** — Request latency, throughput
- **Disk Usage** — Model storage growth

### Alerts
- GPU temperature > 80°C
- VRAM utilization > 90%
- Disk usage > 80%
- Service unhealthy for > 5 minutes

## References

- [STACK_AI_CHECKLIST.md](/STACK_AI_CHECKLIST.md)
- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [OpenWebUI Documentation](https://docs.openwebui.com/)
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

## Security Notes

⚠️ **Important Security Considerations:**
- OpenWebUI authentication is enabled by default
- Change `WEBUI_SECRET_KEY` in production
- API endpoints are exposed on local network only
- Use Tailscale for external access
- Keep GPU drivers and CUDA updated
- Monitor for security advisories on AI model files
