# AI Threat Hunter 

**Deploy an autonomous AI analyst that investigates alerts, queries your SIEM, and produces evidence-backed decisions in minutes instead of hours.**

A Flask-based SOC assistant that enables AI-powered security analysis by connecting to live SIEM data. Built as a lightweight alternative for security teams who need AI assistance without enterprise vendor lock-in.

## 🚀 Core Features

- **Multi-Model AI Support**: Choose between DeepSeek, Google Gemini, and OpenAI models
- **Real-Time SIEM Integration**: Query live security data and let AI analyze the raw results
- **SOC Analysis Templates**: Pre-built templates for incident analysis, threat hunting, and forensic investigation
- **Streaming Responses**: Get AI analysis as it's generated, not after long waits
- **Model Switching**: Change AI providers mid-conversation without losing context
- **Flexible Query Engine**: Execute any SIEM query and have AI analyze the results

## 🔌 SIEM Integrations

### Current
- ✅ **OpenSearch/Elasticsearch** - Query via console proxy pattern with full authentication support

### In Development (Week 4-6)
- 🚧 **Splunk** - Enterprise and Cloud integration
- 🚧 **CrowdStrike Falcon** - EDR alerts and event data
- 🚧 **Microsoft Sentinel** - Azure Sentinel workspace queries

### Planned
- **Elastic Security** - Native Elastic SIEM integration  
- **Chronicle Security** - Google Chronicle support
- **Generic REST API** - Connect to any SIEM with REST endpoints

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- LLM API or LLM access
- Access to SIEMS

### Installation

1. **Clone and install**:
   ```bash
   git clone https://github.com/catgarmara/ai-threat-hunter.git
   cd ai-threat-hunter
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and SIEM credentials
   ```

3. **Run the application**:
   ```bash
   python3 app.py
   ```

4. **Open browser**: http://127.0.0.1:5000

## 📋 SOC Analysis Examples

### Basic Incident Analysis
```bash
curl -X POST http://localhost:5000/soc/analyze \
  -H "Content-Type: application/json" \
  -d '{"incident_data": "Suspicious PowerShell execution detected", "template": "incident_analysis"}'
```

### Query Live SIEM Data
```bash
curl -X POST http://localhost:5000/soc/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "incident_data": "Analyze authentication failures",
    "opensearch_query": {
      "query": {"match": {"event.outcome": "failure"}},
      "size": 100
    }
  }'
```

## 🛠 Architecture

```
ai-threat-hunter/
├── app.py                    # Main Flask application & SOC endpoints
├── ai_clients.py            # Multi-model AI integration
├── config_manager.py        # Environment and configuration
├── opensearch_client_wrapper.py  # SIEM query integration (starting with OpenSearch)
├── error_handler.py         # Error handling and recovery
├── monitoring_manager.py    # Metrics and observability
├── static/                  # Web UI assets
│   ├── index.html          
│   ├── js/main.js          
│   └── css/               
├── security_core/          # Security analysis modules
├── tests/                  # Test suites
└── ccspec/                # Implementation specifications
```

## 🔧 Configuration

### Required Environment Variables
```bash
# AI Model Keys
DEEPSEEK_API_KEY=sk-your-deepseek-key
GEMINI_API_KEY=your-gemini-key  # Optional

# OpenSearch/Elasticsearch (Optional)
OPENSEARCH_HOST=your-opensearch.company.com
OPENSEARCH_PORT=443
OPENSEARCH_USER=your-username
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_INDEX=security-*
OPENSEARCH_SSL=true
```

### API Endpoints

- **Web Interface**: `GET /`
- **Chat**: `POST /chat`
- **SOC Analysis**: `POST /soc/analyze`
- **Health Check**: `GET /health`
- **Metrics**: `GET /performance`
- **SOC Templates**: `GET /soc/templates`

## 📈 Development Roadmap

### Phase 1: Core Platform (Completed)
- ✅ Multi-model AI support (DeepSeek, Gemini, OpenAI)
- ✅ SIEM data integration foundation (OpenSearch)
- ✅ SOC analysis templates
- ✅ Session management and streaming responses

### Phase 2: Universal SIEM Connector (Current)
- 🚧 **Data Source Integration Layer**
  - Splunk Enterprise/Cloud via REST API
  - CrowdStrike Falcon SIEM API connector
  - Microsoft Sentinel KQL queries
  - Elastic Security data streams
- 🚧 **Unified Query Translation**
  - Convert natural language to platform-specific queries
  - Normalize responses across different SIEM formats

### Phase 3: Intelligent Orchestration 
- **Autonomous Investigation Agents**
  - Hypothesis formation from initial alerts
  - Automatic pivot queries based on findings
  - Evidence chain construction
  - MITRE ATT&CK technique mapping
- **Context-Aware Analysis**
  - Historical baseline comparison
  - Entity relationship mapping
  - Threat intelligence enrichment
  - IOC extraction and correlation

### Phase 4: Operational Intelligence 
- **Workflow Automation**
  - Custom agent creation for specific use cases
  - Automated triage and classification
  - Response action recommendations
  - Integration with SOAR platforms
- **Multi-Source Correlation**
  - Cross-SIEM data fusion
  - EDR + SIEM unified analysis
  - Network + endpoint correlation
  - Cloud security posture integration

### Phase 5: Enterprise Features (Future)
- **Deployment Flexibility**
  - Air-gapped deployment option
  - Multi-tenant architecture
  - Role-based access control
  - Audit logging and compliance reporting
- **Advanced Capabilities**
  - Custom model fine-tuning on org data
  - Embedded assistants for existing tools
  - White-label deployment options
  - API-first architecture for integrations

## 🧪 Testing

```bash
# Manual testing interface
python3 manual_test.py

# Test AI model connections
python3 demo_ai_clients.py

# Integration tests
python3 test_flask_integration.py

# OpenSearch connectivity test
python3 security_core/tests/test_savedcard_alert.py
```

## 🤝 Contributing

This is an open-source prototype actively being developed. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

Priority areas for contribution:
- Additional SIEM connectors
- Hunt pack templates
- AI prompt optimization
- Security analysis improvements

## 📚 Documentation

- [Configuration Reference](CONFIGURATION_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Development Notes](CLAUDE.md)
- [Implementation Plans](ccspec/)

## ⚠️ Disclaimer

This is a prototype tool for security analysis. Always verify AI-generated analysis with human expertise. Not intended as a replacement for professional security analysts or commercial SOC platforms.
