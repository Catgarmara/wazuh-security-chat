# Wazuh AI Companion

Proof-of-concept utilities that plug large-language-model helpers into **WAZUH** for faster threat hunting and alert triage.

* **Scope:** Demo-grade, not production—see ⚠️ *Limitations*.
* **Blog source:** Based on ideas from Wazuh's "Leveraging Artificial Intelligence for Threat Hunting" (July 2025).

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VM1: WAZUH    │    │ VM2: Metasploit3 │    │  VM3: ParrotOS  │
│   SIEM/Manager  │◄───┤  + Wazuh Agent   │◄───┤  Attack Machine │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         │ SSH/Log Export
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Localhost (RTX 3080 AI Workstation)                │
│  ┌─────────────────┐    ┌──────────────────┐                    │
│  │  FastAPI +      │    │   Qwen3:8b LLM   │                    │
│  │  WebSocket UI   │◄──►│  via Ollama      │                    │
│  └─────────────────┘    └──────────────────┘                    │
│           │                       ▲                             │
│           ▼                       │                             │
│  ┌─────────────────┐    ┌──────────────────┐                    │
│  │  FAISS Vector   │    │  HuggingFace     │                    │
│  │  Store (Logs)   │◄──►│  Embeddings      │                    │
│  └─────────────────┘    └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

**Flow:**
1. **Attack Simulation:** ParrotOS (VM3) generates malicious traffic against Metasploitable3 (VM2)
2. **Detection:** Wazuh agent on VM2 forwards logs to Wazuh manager (VM1)
3. **AI Analysis:** Local GPU-accelerated Llama3 model processes alerts via FastAPI
4. **Output:** Enhanced threat intelligence and automated triage recommendations

## Features

- [x] **Alert Ingestion:** REST API endpoint for Wazuh alert JSON
- [x] **Sigma Rule Integration:** Custom detection rules with unit testing
- [ ] **LLM-Powered Analysis:** Contextual threat hunting assistance
- [ ] **Automated Triage:** Priority scoring and response recommendations
- [ ] **Docker Deployment:** Single-command setup via docker-compose

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/wazuh-ai-companion
cd wazuh-ai-companion

# Run with Docker
docker compose up -d

# Test API endpoint
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d @samples/sample_alert.json
```

## Sample Data

The `samples/` directory contains 20 real Wazuh alerts exported from a lab environment, covering:
- Web application attacks (SQLi, XSS)
- Privilege escalation attempts
- Suspicious PowerShell activity
- Network reconnaissance

## Roadmap

| Milestone | ETA | Status | Notes |
|-----------|-----|--------|-------|
| Repo bootstrap | 29 Jul 2025 | ✅ | README + MIT license |
| FastAPI + OpenAI skeleton | 29 Jul 2025 evening | 🟡 | Task T-3 in progress |
| Docker-compose wrapper | 30 Jul 2025 | 🟡 | Task T-4 |
| Sigma rules library | 31 Jul 2025 | 🟡 | 2+ custom detection rules |
| Demo GIF + v0.1 release | 31 Jul 2025 | 🟡 | 20-second usage demo |

## ⚠️ Limitations

- **Demo purposes only** - not hardened for production use
- **API keys in plaintext** - ~~not applicable with local model~~  
- **No authentication** - endpoints are publicly accessible
- **Limited error handling** - may fail on malformed input
- **Resource intensive** - requires GPU for optimal LLM performance

## Tech Stack

- **Backend:** FastAPI (Python 3.9+)
- **AI/ML:** Llama3 local model, RTX 3080 GPU acceleration
- **SIEM:** Wazuh 4.12 (OVA deployment)
- **Testing:** Metasploitable3 + ParrotOS attack simulation
- **Deployment:** Docker Compose
- **CI/CD:** GitHub Actions

## Contributing

This is a proof-of-concept for job application purposes. Issues and PRs welcome for educational improvements!

## References

* Wazuh. "Leveraging Artificial Intelligence for Threat Hunting in Wazuh."  
  <https://wazuh.com/blog/leveraging-artificial-intelligence-for-threat-hunting-in-wazuh/>
* MITRE ATT&CK Framework: <https://attack.mitre.org/>
* Sigma Detection Rules: <https://github.com/SigmaHQ/sigma>
