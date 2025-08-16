# MCP Gateway MIA - Intent-Aware Security Layer

**Intent-aware security layer for MCP (Model Context Protocol) interactions.**

Instead of asking *"Can this client access this tool?"*, MIA asks: *"Does this transaction serve the agreed intent between client and server?"*

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd mcpgw

# One-command setup (installs Ollama, pulls models, sets up environment)
./setup.sh

# Start all services
./start.sh

# Run complete demonstration
./demo.sh
```

## 🎯 What is MIA?

**Mutual Intent Agreement (MIA)** is a new approach to AI tool security that replaces static permission systems with dynamic, semantic understanding of client intentions and server capabilities.

### The Paradigm Shift

**Traditional Security:**
- Static permission lists
- "Can user X access tool Y?"
- Binary allow/deny decisions
- No understanding of purpose

**MIA Security:**
- Dynamic intent analysis
- "Does this transaction serve the agreed purpose?"
- Semantic understanding of interactions
- Context-aware security decisions

## 🏗️ How MIA Works

### 3-Phase Process

#### Phase 1: Declaration
- **Clients** declare their intent: *"I need weather data for travel planning"*
- **Servers** register capabilities: *"I provide public weather data, no tracking"*

#### Phase 2: Negotiation
- **LLM analyzes** semantic compatibility between intent and capability
- **Creates binding contract** with agreed terms and constraints
- **Establishes trust** through mutual understanding

#### Phase 3: Validation
- **Every transaction** validated against the agreed intent
- **Real-time monitoring** for intent drift and violations
- **Bidirectional protection** for both clients and servers

### Example Flow

```python
# Client declares intent
client_intent = {
    "purpose": "I need weather data for travel planning",
    "constraints": ["no_personal_data", "read_only", "public_data_only"],
    "data_requirements": ["current_weather", "forecasts"]
}

# Server registers capability
server_capability = {
    "provides": ["weather_data", "forecasts"],
    "boundaries": ["no_pii", "public_data_only"],
    "supported_operations": ["read"]
}

# LLM analyzes compatibility
compatibility = await analyzer.analyze_intent_compatibility(
    client_intent, server_capability
)

# Contract created if compatible
if compatibility.status == "compatible":
    contract = IntentContract(
        agreed_purpose=client_intent.purpose,
        constraints=client_intent.constraints + compatibility.suggested_constraints
    )
```

## 🛡️ Bidirectional Protection

MIA protects **both parties** in AI tool interactions:

### Server Protection
- Validates client requests against declared intent
- Prevents scope creep and malicious usage
- Detects intent drift over time

### Client Protection (Enhanced Feature)
- Validates server responses against client constraints
- Prevents data leakage and privacy violations
- Blocks tracking attempts and unexpected data

### Protection Examples

**Scenario 1: Intent Violation (Server Protection)**
```
Client Intent: "Weather data for travel planning"
Malicious Request: get_personal_location_history()
MIA Action: ❌ BLOCKED - Violates travel planning intent
```

**Scenario 2: Privacy Violation (Client Protection)**
```
Client Constraint: "no_location_tracking"
Server Response: { weather: "sunny", user_location: "37.7749,-122.4194" }
MIA Action: ❌ BLOCKED - Violates no tracking constraint
```

## 🧠 LLM-Powered Analysis

MIA uses sophisticated LLM analysis for semantic understanding:

### Intent Compatibility Analysis
```python
system_prompt = """You are an AI security analyst specializing in Mutual Intent Agreement (MIA) systems. Your role is to perform deep semantic analysis of client intentions and server capabilities to determine compatibility for secure AI tool interactions.

CORE PRINCIPLES:
1. Semantic Understanding: Analyze the MEANING and PURPOSE behind requests
2. Intent Alignment: Evaluate if client's declared purpose aligns with server capabilities
3. Risk Assessment: Identify potential security, privacy, and misuse risks
4. Constraint Synthesis: Recommend specific constraints to ensure safe interaction"""
```

### Real-time Transaction Validation
- Every request analyzed for intent alignment
- Context-aware security decisions
- Detailed reasoning for all decisions
- Confidence scoring and risk assessment

## 📊 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MIA Gateway   │    │  Ollama Client  │    │ Weather Server  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │IntentBroker │ │◄──►│ │LLM Analysis │ │    │ │ MCP Tools   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │                 │    │                 │
│ │ Contracts   │ │    │ gpt-oss20b-128k │    │ FastAPI Server  │
│ └─────────────┘ │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Travel Client   │
                    │                 │
                    │ Python Client   │
                    │ Demonstrates    │
                    │ Complete MIA    │
                    └─────────────────┘
```

### Core Components

- **IntentBroker**: Orchestrates the 3-phase MIA process
- **IntentAnalyzer**: LLM-powered semantic analysis using local Ollama
- **IntentContract**: Binding agreements with lifecycle management
- **MIA Gateway**: FastAPI application with intent validation middleware

## 🔧 API Endpoints

### Intent Management
- `POST /intent/declare` - Client declares intent
- `POST /capability/register` - Server registers capabilities
- `POST /intent/negotiate` - Negotiate intent contract
- `GET /intent/contracts` - List active contracts
- `GET /intent/capabilities` - List server capabilities

### Transaction Processing
- `POST /mcp/request` - Intent-validated MCP proxy
- `GET /intent/violations` - View contract violations
- `GET /status` - System status and monitoring

### Example API Usage
```bash
# Declare client intent
curl -X POST http://localhost:8000/intent/declare \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "I need weather data for travel planning",
    "data_requirements": ["current_weather", "forecasts"],
    "constraints": ["no_personal_data", "read_only"]
  }'

# Negotiate contract
curl -X POST http://localhost:8000/intent/negotiate \
  -H "Content-Type: application/json" \
  -d '{
    "client_intent_id": "intent-123",
    "server_capability_id": "weather-server-456"
  }'

# Make validated request
curl -X POST http://localhost:8000/mcp/request \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "contract-789",
    "server_name": "weather-server",
    "request": {
      "method": "tools/call",
      "params": {
        "name": "get_current_weather",
        "arguments": {"location": "Paris"}
      }
    }
  }'
```

## 🐳 Local Development

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- macOS (for Ollama integration)

### Setup
```bash
# Complete setup (one command)
./setup.sh

# Manual setup
brew install ollama
ollama pull gpt-oss20b-128k
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Development Commands
```bash
# Start all services
./start.sh

# Stop all services
./stop.sh

# Clean restart
./stop.sh --clean && ./start.sh

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Run demo
./demo.sh
```

### Service URLs
- **MIA Gateway**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Gateway Health**: http://localhost:8000/health
- **Ollama API**: http://localhost:11434

## 📋 Demo Scenarios

The included demo showcases:

### 1. Basic MIA Flow
- Intent declaration and capability registration
- LLM-powered compatibility analysis
- Contract negotiation and activation

### 2. Intent-Validated Requests
- Weather requests aligned with travel planning intent
- Real-time validation against contract terms

### 3. Violation Detection
- Attempts to access data outside declared intent
- Automatic blocking with detailed reasoning

### 4. Python Client Integration
- Complete application using MIA
- Multi-destination trip planning
- Session management and error handling

### 5. Bidirectional Protection
- Server response validation
- Privacy violation detection
- Client protection from malicious servers

## 🔍 Example Output

```bash
🔐 Demo 1: Basic Mutual Intent Agreement Flow
==============================================
[SUCCESS] Intent declared successfully!
[SUCCESS] Contract negotiated successfully!
[DEMO] Contract ID: b9fc1ff8-be7d-47fd-a6cc-585e698d8abf

🌤️ Demo 2: Intent-Validated MCP Requests
==========================================
[SUCCESS] Weather request validated and processed!
[SUCCESS] Forecast request validated and processed!

🚨 Demo 3: Intent Violation Detection
=====================================
[SUCCESS] Intent violation correctly detected and blocked!
[DEMO] Validation Result: invalid
[DEMO] Reasons: ['The request calls `get_personal_location_history`, which retrieves personal location data.', 'This violates the constraint `no_personal_data_storage`...']
```

## 🎯 Key Benefits

### For Developers
- **Semantic Security**: Understanding of intent, not just permissions
- **Dynamic Policies**: Security adapts to declared purposes
- **Transparent Decisions**: Every security decision explained
- **Bidirectional Trust**: Protection for both clients and servers

### For Organizations
- **Reduced Risk**: Intent-aware security prevents misuse
- **Audit Trail**: Complete record of all interactions and decisions
- **Compliance**: Built-in privacy and data protection
- **Scalability**: No static permission lists to maintain

### For AI Systems
- **Context Awareness**: Security decisions based on purpose
- **Intent Drift Detection**: Automatic detection of changing behavior
- **Adaptive Protection**: Security evolves with usage patterns
- **Mutual Trust**: Both parties protected through verified intent

## 🚀 A next step in AI Security

MIA represents a shift in how we think about AI tool security:

- **From Permissions to Intent**: Understanding purpose, not just access
- **From Static to Dynamic**: Security that adapts to context
- **From One-sided to Mutual**: Protection for all parties
- **From Binary to Semantic**: Nuanced understanding of interactions

## 📚 Technical Details

### Data Models
- **ClientIntentDeclaration**: Client's declared purpose and constraints
- **ServerCapabilityDeclaration**: Server's capabilities and boundaries
- **IntentContract**: Binding agreement with lifecycle management
- **IntentTransactionValidation**: Real-time validation results

### LLM Integration
- **Local Ollama**: No cloud dependencies, complete privacy
- **128K Context Window**: Handles complex intent analysis
- **Sophisticated Prompts**: Deep semantic understanding
- **Confidence Scoring**: Quantified trust in decisions

### Monitoring & Analytics
- **Real-time Metrics**: Transaction success rates, violations
- **Intent Drift Analysis**: Detection of changing behavior patterns
- **Contract Lifecycle**: Creation, validation, expiration tracking
- **Audit Logging**: Complete record of all security decisions

## 🤝 Contributing

This project demonstrates the first practical implementation of intent-aware AI tool governance. Contributions welcome for:

- Additional intent patterns and templates
- Enhanced LLM analysis capabilities
- New MCP server integrations
- Security policy improvements

## 📄 License

MIT License - See LICENSE file for details.

---

**MIA represents a next step in AI tool security - where intent alignment replaces permission management, creating truly intelligent and adaptive security systems.**

🚀 **Ready to see intent-aware security in action? Run `./demo.sh` and see how it works!**
