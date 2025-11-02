# AI Stack Quick Reference

## Quick Deploy
```bash
cd /opt/stacks/stack-ai
docker-compose up -d
```

## Service URLs
- **Ollama API**: http://localhost:11434
- **OpenWebUI**: http://localhost:3000
- **Stable Diffusion**: http://localhost:7860

## Quick Checks
```bash
# Health status
docker-compose ps

# Ollama models
docker exec ollama ollama list

# GPU usage
nvidia-smi

# Logs
docker-compose logs -f [service]
```

## Pull First Model
```bash
docker exec ollama ollama pull llama2
```

## Data Locations
- Ollama: `/srv/ai_data/ollama`
- OpenWebUI: `/srv/ai_data/openwebui`
- Stable Diffusion: `/srv/ai_data/stable-diffusion`
