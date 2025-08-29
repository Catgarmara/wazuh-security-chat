AI Threat Hunter (Open-Source Prototype)

A Flask-based agentic SOC copilot that runs targeted hunts, executes investigations, and produces evidence-linked recommendations. Built as a lightweight alternative to commercial AI SOC assistants (e.g., Dropzone, Simbian, Legion).

🚀 Core Features

Agentic Investigations: Forms hypotheses, queries SIEM data (currently OpenSearch), pivots across results, enriches with OSINT, maps to MITRE ATT&CK, and outputs incident narratives, IOCs, and recommended actions.

Hunt Packs (Web/Auth Focus): Credential abuse, suspicious logins, traversal/injection attempts, admin-panel probing.

Multi-Model Engine: Supports multiple LLMs (DeepSeek, Gemini, OpenAI, local air-gapped models) with real-time streaming, retry/fallback, and model switching mid-conversation.

SOC Integration: Prebuilt analysis templates for incident classification, triage summaries, and remediation steps.

Operational Guardrails: Input validation, rate limiting, API key isolation, audit logging, health/metrics endpoints.

Proven Impact: Internal application of this approach cut L1 triage from ~30 min to ~5 min (~83%) and standardized analyst output.

🔌 Integrations

Current: OpenSearch (console-proxy query pattern)

In Progress: CrowdStrike Falcon EDR (alerts + event data) ← next milestone

Planned: Splunk, QRadar, Microsoft Sentinel, Elastic Security, Chronicle

🛠 Tech Stack

Python / Flask

OpenSearch (SIEM integration)

LLM APIs (DeepSeek, Gemini, OpenAI) + local LLM support

SSE streaming, REST endpoints

Regex / JSON normalization

Dockerized deployment

📂 Project Structure
ai-threat-hunter/
├── app.py                # Main Flask app  
├── ai_clients.py         # Multi-model LLM integration  
├── soc_templates.py      # Incident analysis & hunt packs  
├── opensearch_client.py  # SIEM query integration  
├── config_manager.py     # Config & environment variables  
├── monitoring/           # Metrics & observability  
├── static/               # Web UI (HTML/CSS/JS)  
├── tests/                # Manual & automated tests  
└── docs/                 # Deployment & config guides

📈 Roadmap

    Short Term (current):

        Expand CrowdStrike Falcon connector (alerts + event search)

        Additional SOC templates for EDR + hybrid telemetry

    Medium Term (4–8 weeks):

        Splunk & QRadar integration

        Sentinel workspace queries

        Cross-SIEM correlation

    Long Term:

        Universal API connector for arbitrary SIEM/EDR platforms

        Advanced hunt-pack marketplace

🔒 Security

    Input validation & sanitization

    Rate limiting

    API key security (env-based)

    Audit logging of all queries & responses

📄 License

This project is provided as-is for educational and development purposes.
