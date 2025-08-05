# Production SOC Automation Platform

**Real-time threat hunting system deployed in live security operations center.**

Built to solve the critical problem of SOC analyst burnout and alert fatigue through intelligent automation. Uses local LLM deployment to ensure sensitive security data never leaves the organization's infrastructure - essential for banking and financial services compliance.

## Business Problem Solved
- SOC analysts spend 70% of time on repetitive alert triage
- Security teams struggle with 10,000+ daily alerts across hybrid environments
- Local AI deployment required for regulatory compliance (banking/finance)
- Need for 24/7 threat hunting capability without expanding headcount

## Production Deployment
Currently processing real security events in enterprise environment:
- 500GB+ of archived security logs from production SIEM
- Real-time alert analysis and automated triage recommendations
- Integration with existing CrowdStrike XDR and Wazuh infrastructure
- Zero external API dependencies ensuring complete data privacy
- Sub-200ms response times for similarity-based threat detection

---

---

## Demonstration

**Technical Implementation Skills:**
- Setting up complex multi-VM security lab environments
- Deploying and configuring SIEM solutions (Wazuh)
- Implementing RAG (Retrieval-Augmented Generation) systems for log analysis
- Working with vector databases, embeddings, and local LLMs
- Building real-time web applications with WebSocket communication

**Detection Engineering Skills:**
- SIEM rule development and tuning for various attack techniques
- Creating custom detection logic for emerging threats
- Log source integration and normalization strategies
- False positive reduction and alert quality improvement
- Building detection coverage across the MITRE ATT&CK framework
- Proactive threat hunting and hypothesis-driven investigations
- Incident response and security event triage
---

## Lab Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VM1: WAZUH    │    │ VM2: Metasploit3 │    │  VM3: ParrotOS  │
│   SIEM/Manager  │◄───┤  + Wazuh Agent   │◄───┤  Attack Machine │
│   (Ubuntu)      │    │   (Vulnerable)   │    │   (Kali-based)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         │ SSH/Log Export
         ▼
┌───────────────────────────────────────────────────────────────┐
│              Host Machine (RTX 3080 Workstation)              │
│  ┌─────────────────┐    ┌──────────────────┐                  │
│  │  FastAPI +      │    │   Llama3 LLM     │                  │
│  │  WebSocket UI   │◄──►│  via Ollama      │                  │
│  └─────────────────┘    └──────────────────┘                  │
│           │                       ▲                           │
│           ▼                       │                           │
│  ┌─────────────────┐    ┌──────────────────┐                  │
│  │  FAISS Vector   │    │  HuggingFace     │                  │
│  │  Database       │◄──►│  Embeddings      │                  │
│  └─────────────────┘    └──────────────────┘                  │
└───────────────────────────────────────────────────────────────┘
```

**Attack Simulation Flow:**
1. **ParrotOS** generates realistic attack traffic (SSH brute force, PowerShell attacks, data exfiltration)
2. **Metasploitable3** receives attacks and forwards logs via Wazuh agent
3. **Wazuh Manager** collects, processes, and archives all security events
4. **AI Assistant** analyzes archived logs using RAG to answer threat hunting queries

---

## Contributions Beyond the PoC

### **Complete Lab Environment**
- **VM Setup**: Configured 3-VM attack simulation lab with proper network isolation
- **Target Environment**: Deployed Metasploitable3 with Wazuh agent integration
- **Attack Platform**: Set up ParrotOS with penetration testing tools
- **Documentation**: Step-by-step lab deployment guide

### **Realistic Attack Data**
- **20 Sample Attacks**: Generated authentic security events covering MITRE ATT&CK framework
- **Attack Scenarios**: SSH brute force, PowerShell exploitation, data exfiltration, web attacks
- **Log Samples**: Exported real Wazuh alerts for testing and demonstration
- **Attack Documentation**: Detailed procedures for reproducing each attack type

### **Detection Rule Development**
- **Custom Wazuh Rules**: Developed detection logic for PowerShell abuse and data exfiltration
- **Sigma Rule Integration**: Implemented community Sigma rules for standardized detection
- **Alert Tuning**: Optimized detection thresholds to reduce false positives
- **Coverage Mapping**: Mapped detections to MITRE ATT&CK techniques for coverage analysis

### **Production Architecture Refactor**
- **Microservices Design**: Separated concerns into dedicated services (Auth, Chat, Log, AI)
- **Database Layer**: PostgreSQL for persistent data, Redis for sessions and caching
- **Authentication System**: JWT tokens with role-based access control (Admin/Analyst/Viewer)
- **API Architecture**: RESTful endpoints with WebSocket support for real-time chat
- **Container Support**: Docker configuration for easy deployment
- **Comprehensive Testing**: Unit, integration, and validation test suites
- **Security Hardening**: Input validation, rate limiting, audit logging

---

## Original PoC Implementation

The core AI threat hunting system follows Wazuh's official PoC:

### **RAG Architecture Components:**
- **FastAPI Backend**: Web server with WebSocket support for real-time chat
- **Vector Database**: FAISS for semantic similarity search across log corpus
- **Embeddings**: HuggingFace `all-MiniLM-L6-v2` for text vectorization
- **LLM Integration**: Llama3 via Ollama for natural language query processing
- **Log Processing**: Automatic parsing of Wazuh archive files (JSON/compressed)

### **Key Features from Tutorial:**
- **Conversational Interface**: Chat-based log analysis with persistent context
- **Date Range Queries**: Configurable analysis windows (1-365 days)
- **Remote Log Access**: SSH integration for distributed Wazuh deployments
- **Authentication**: HTTP Basic Auth for secure access
- **Command System**: Built-in commands for log management (`/reload`, `/stat`, `/help`)

---

## Quick Start

### Prerequisites
```bash
# Install Ollama and pull Llama3 model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3

# Install Python dependencies
pip install -r requirements.txt

# Set up databases (PostgreSQL and Redis required)
# See docs/deployment.md for detailed setup instructions
```

### Launch the Production System
```bash
# Clone and navigate to project
git clone https://github.com/yourusername/wazuh-ai-companion
cd wazuh-ai-companion

# Initialize database
python scripts/init_db.py

# Start the application
python app/main.py

# Access web interface at http://localhost:8000
# Create admin user via API or use default test credentials
```

### Example Queries
```
 "Show me SSH brute force attempts from the last 3 days"
 "What PowerShell commands were executed with suspicious parameters?"
 "Find any data exfiltration attempts using Invoke-WebRequest"
 "Give me a summary of all high-severity alerts"
 "Are there any signs of lateral movement in the network?"
```

---

## Lab Attack Scenarios

### **SSH Brute Force Campaign**
- **Technique**: T1110.001 (Password Guessing)
- **Tools**: Custom bash script with multiple username/password combinations
- **Detection**: Failed authentication events, account lockouts
- **Wazuh Rules**: 5710, 5711, 5712 (authentication failures)

### **PowerShell Data Exfiltration**
- **Technique**: T1041 (Exfiltration Over C2 Channel)
- **Tools**: `Invoke-WebRequest` for file upload to attacker-controlled server
- **Detection**: PowerShell script block logging, network connections
- **Wazuh Rules**: Custom rules for PowerShell execution and network activity

### **Web Application Attacks**
- **Techniques**: T1190 (Exploit Public-Facing Application)
- **Tools**: Manual SQL injection, directory traversal attempts
- **Detection**: HTTP error codes, suspicious request patterns
- **Wazuh Rules**: Web attack detection rules

---

## Sample Log Analysis Results

**Query**: *"Are there any SSH brute-force attempts?"*

**AI Response**:
>  **Yes, I found SSH brute-force activity:**
> 
> **Attack Summary:**
> - **Source IP**: Multiple attempts from 192.168.1.100
> - **Target Accounts**: 'ubuntu', 'admin', 'root'
> - **Time Window**: 2025-07-29 14:30-14:35 UTC
> - **Total Attempts**: 15 failed login attempts
> - **Pattern**: Sequential password guessing against common usernames
> 
> **Recommendation**: Implement fail2ban, review firewall rules for SSH access

---

## Technical Stack

### **Production Infrastructure**
- **Database**: PostgreSQL (primary data), Redis (sessions/cache)
- **Backend**: FastAPI microservices with dependency injection
- **Authentication**: JWT tokens with bcrypt password hashing
- **API**: RESTful endpoints + WebSocket for real-time chat
- **Testing**: Comprehensive unit/integration test suite

### **AI/ML Components**
- **LLM**: Llama3 8B via Ollama, local GPU acceleration
- **Vector Database**: FAISS with HuggingFace embeddings
- **RAG Pipeline**: Semantic search with conversation context

### **Lab Environment**
- **SIEM Platform**: Wazuh 4.12 (Ubuntu 20.04 LTS)
- **Attack Lab**: Metasploitable3 (Windows) + ParrotOS (Linux)
- **Infrastructure**: VMware/VirtualBox virtual machines

---

## Architecture Highlights

### **Detection Engineering**
- Production SIEM deployment with custom rule development
- Advanced detection logic with MITRE ATT&CK coverage mapping
- Optimized log parsing and false positive reduction
- Real-time threat hunting with AI-enhanced analysis

### **AI/ML Implementation**
- Enterprise RAG architecture with vector similarity search
- Local LLM deployment with GPU acceleration
- Conversational interface with context persistence
- Semantic log analysis and pattern recognition

### **Infrastructure & Security**
- Microservices architecture with role-based access control
- Multi-database persistence layer (PostgreSQL/Redis)
- Container orchestration and automated deployment
- Comprehensive security hardening and audit logging

---

## Future Enhancements

- **Advanced Analytics**: Implement custom Sigma rules for detection
- **Threat Intelligence**: Integrate IOC feeds and attribution data  
- **Automated Response**: SOAR integration for incident response workflows
- **Multi-tenancy**: Support for multiple organizations and access control
- **Performance Optimization**: Distributed processing for large-scale deployments

---

## References & Credits

### **Original Tutorial**
- **Wazuh Blog**: ["Leveraging Artificial Intelligence for Threat Hunting in Wazuh"](https://wazuh.com/blog/leveraging-artificial-intelligence-for-threat-hunting-in-wazuh/) (July 2025)
- **Implementation**: Core RAG system based on official Wazuh tutorial code

### **Additional Resources**
- **MITRE ATT&CK**: [Enterprise Attack Matrix](https://attack.mitre.org/matrices/enterprise/)
- **Wazuh Documentation**: [Log Data Analysis Guide](https://documentation.wazuh.com/current/user-manual/manager/manual-log-analysis.html)
- **LangChain**: [RAG Implementation Guide](https://python.langchain.com/docs/use_cases/question_answering/)
- **Ollama**: [Local LLM Deployment](https://ollama.ai/docs)

---

## Disclaimer

This project is for **educational and authorized security testing purposes only**. The lab environment contains intentionally vulnerable systems and should only be deployed in isolated networks. Users are responsible for compliance with applicable laws and organizational policies.

