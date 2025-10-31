---
title: "ORESI // SYSTEMS — Homelab Handbook: Vision Overview"
tags: [homelab, architecture, vision, roadmap]
date: 2025-10-29
author: "ORESI"
theme: auto
---

# 🧠 ORESI // SYSTEMS  
## Homelab Handbook: Vision Overview  

> ⚡ **Mission:** Build a resilient, intelligent, and modular homelab ecosystem that unifies compute, storage, and automation — designed for *performance, scalability,* and *personal sovereignty*.

---

## 🗺️ Table of Contents
1. [Vision Statement](#vision-statement)
2. [Core Principles](#core-principles)
3. [Long-Term Goals](#long-term-goals)
4. [System Overview](#system-overview)
5. [Strategic Phases](#strategic-phases)
6. [Tools & Philosophy](#tools--philosophy)

---

## 1. 🎯 Vision Statement
Your homelab is not just a sandbox — it’s an **ecosystem**.  
It unites:
- **Proxmox cluster** → High-availability compute core  
- **Synology NAS (Blackbox)** → Central data repository  
- **Mac Minis (M4 & Intel)** → Specialized edge nodes (AI + automation)  
- **Tailscale mesh** → Secure, zero-config interconnect  

Goal:  
> **“One network. Many nodes. Unified automation.”**

---

## 2. ⚙️ Core Principles

| Principle | Description | Symbol |
|------------|--------------|---------|
| 🔁 **Redundancy** | Every service has failover or recovery strategy | ♻️ |
| 🧩 **Modularity** | All services are Dockerized and isolated by stack | 🧱 |
| 🌐 **Accessibility** | Global reach via Tailscale + reverse proxy | 🌍 |
| 🔒 **Privacy** | All data lives locally, encrypted backups only | 🔐 |
| ⚡ **Automation** | No manual deployment — everything scripted | 🤖 |

---

## 3. 🚀 Long-Term Goals
- Centralized service orchestration via **Dockge** and GitOps.  
- Fully local AI inference using **Ollama** + **OpenWebUI**.  
- Modular deployment using **Docker Compose stacks**:  
  - `stack-infra`, `stack-media`, `stack-content`, `stack-ai`, `stack-smarthome`.
- Automatic sync between **Synology (NFS)** and **Proxmox nodes**.
- Unified SSO via **Authelia** (optional phase 3).

---

## 4. 🏗️ System Overview

**Physical Nodes**
```
Whitebox (192.168.0.101) - PVE-Core
Redbox   (192.168.0.100) - PVE-Media
Bloodbox (192.168.0.103) - PVE-Compute
Blackbox (192.168.0.40)  - Synology NAS
Mac Mini M4 (192.168.0.53) - AI / LLM Node
Mac Mini Intel (TBD) - Utility / Backup Node
```

**Folder Hierarchy (Synology)**
```
/volume2/data/
├── media/
│   ├── movies/
│   ├── tv/
│   ├── music/
│   ├── photos/
│   ├── books/
│   ├── videos/
│   └── porn/
├── downloads/
│   ├── complete/
│   │   ├── radarr/
│   │   └── sonarr/
│   └── incomplete/
├── backups/
└── docker_data/
```

---

## 5. 🧩 Strategic Phases

| Phase | Description | Key Outcome |
|-------|--------------|--------------|
| 1️⃣ | Infrastructure Foundation | 3-node Proxmox cluster operational |
| 2️⃣ | Synology Storage Integration | Centralized NFS + Docker data pool |
| 3️⃣ | Network Security Mesh | Tailscale mesh with MagicDNS |
| 4️⃣ | Docker VM Deployment | Containers orchestrated via Dockge |
| 5️⃣ | GitOps Automation | All configs version-controlled |
| 6️⃣ | AI & Smart Home Layer | Ollama, OpenWebUI, Home Assistant |
| 7️⃣ | Maintenance & Backups | Nightly jobs + auto-recovery routines |

---

## 6. 🛠️ Tools & Philosophy

### 🧠 Philosophy
- **Automate first, debug second.**
- **Never configure twice.** Save configs to Git.
- **Keep services small, atomic, and backed up.**

### 🧰 Core Tools
| Tool | Function |
|------|-----------|
| 🐳 Docker | Container engine |
| ⚙️ Dockge | Stack UI management |
| 🧠 Ollama | LLM inference |
| 🌐 Tailscale | Secure network layer |
| 🏡 Home Assistant | Smart home control |
| 📈 Uptime Kuma | Monitoring |
| 🔍 Meilisearch | Local search |
| 💾 Synology DSM | Data foundation |

---

> 🧾 **Note:**  
> Keep this file at the root of your Obsidian vault for context.  
> Each subsequent section (02, 03, etc.) builds from this vision.

---
