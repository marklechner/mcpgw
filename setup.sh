#!/bin/bash

# MCP Gateway MIA Setup Script
# Installs and configures everything needed for local development

set -e

echo "🚀 Setting up MCP Gateway with Mutual Intent Agreement (MIA)"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This setup script is designed for macOS. Please adapt for your OS."
    exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker Desktop from https://docker.com"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please update Docker Desktop."
    exit 1
fi

# Check if Python 3.9+ is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_error "Python 3.9+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Prerequisites check passed"

# Create necessary directories
print_status "Creating project directories..."
mkdir -p logs
mkdir -p config
mkdir -p data
mkdir -p docker/grafana/dashboards
mkdir -p docker/grafana/datasources

# Create Python virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source venv/bin/activate

# Create requirements.txt if it doesn't exist
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << EOF
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
aiohttp>=3.9.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-dotenv>=1.0.0
structlog>=23.2.0
prometheus-client>=0.19.0
pyyaml>=6.0.1
jinja2>=3.1.2
EOF
fi

pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

# Create configuration files
print_status "Creating configuration files..."

# Create MIA Gateway configuration
cat > config/mia_config.yml << EOF
# MIA Gateway Configuration

# Server settings
server:
  host: "0.0.0.0"
  port: 8000
  reload: true
  log_level: "info"

# Ollama LLM settings
ollama:
  url: "http://localhost:11434"
  model: "llama3.1"
  timeout: 30
  max_retries: 3

# Intent analysis settings
intent_analysis:
  confidence_threshold: 0.7
  max_analysis_time: 10
  enable_drift_detection: true
  drift_analysis_window_hours: 24

# Contract settings
contracts:
  default_duration_minutes: 120
  max_duration_minutes: 1440  # 24 hours
  cleanup_interval_minutes: 5
  max_violations_before_deactivation: 5

# Security settings
security:
  enable_request_logging: true
  log_sensitive_data: false
  max_request_size: 1048576  # 1MB
  rate_limiting:
    enabled: true
    default_requests_per_minute: 60

# Monitoring
monitoring:
  enable_metrics: true
  metrics_port: 9000
  health_check_interval: 30

# Logging
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/mia_gateway.log"
  max_size_mb: 100
  backup_count: 5
EOF

# Create intent templates
cat > config/intent_templates.yml << EOF
# Common Intent Templates for MIA

common_intents:
  data_analysis:
    purpose_patterns:
      - "analyze"
      - "research" 
      - "study"
      - "investigate"
    allowed_operations: ["read", "aggregate", "compute"]
    forbidden_operations: ["modify", "delete", "export"]
    typical_constraints:
      - "read_only_access"
      - "no_personal_data"
      - "aggregated_results_only"

  travel_planning:
    purpose_patterns:
      - "travel"
      - "trip"
      - "vacation"
      - "journey"
    allowed_operations: ["read", "query", "forecast"]
    data_requirements:
      - "weather_data"
      - "location_info"
      - "public_information"
    typical_constraints:
      - "public_data_only"
      - "no_location_tracking"
      - "travel_context_only"

  business_intelligence:
    purpose_patterns:
      - "business"
      - "market"
      - "financial"
      - "commercial"
    allowed_operations: ["read", "analyze", "report"]
    forbidden_operations: ["trade", "execute", "modify"]
    typical_constraints:
      - "read_only_access"
      - "no_trading_actions"
      - "reporting_only"

server_capabilities:
  weather_service:
    provides: ["weather_data", "forecasts", "climate_info"]
    boundaries: ["public_data_only", "no_personal_tracking"]
    data_sensitivity: "public"
    
  financial_data:
    provides: ["market_data", "prices", "analytics"]
    boundaries: ["no_trading", "read_only", "delayed_data"]
    data_sensitivity: "restricted"
    
  document_service:
    provides: ["document_search", "content_analysis"]
    boundaries: ["no_modification", "read_only", "metadata_only"]
    data_sensitivity: "confidential"
EOF

# Create Dockerfile for gateway
cat > docker/Dockerfile.gateway << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "src.mcpgw.gateway.mia_gateway", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Create Dockerfile for weather server
cat > docker/Dockerfile.weather-server << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8001

# Run the weather server
CMD ["python", "-m", "src.mcpgw.examples.weather_server.weather_mcp_server"]
EOF

# Create Dockerfile for demo client
cat > docker/Dockerfile.demo-client << EOF
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create logs directory
RUN mkdir -p logs

# Run the demo client
CMD ["python", "-m", "src.mcpgw.examples.portfolio_client.travel_planner_client"]
EOF

# Create Prometheus configuration
cat > docker/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mia-gateway'
    static_configs:
      - targets: ['mia-gateway:9000']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'weather-server'
    static_configs:
      - targets: ['weather-server:8001']
    scrape_interval: 15s
    metrics_path: /metrics
EOF

# Create Grafana datasource configuration
cat > docker/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

print_success "Configuration files created"

# Check if Ollama is installed locally
print_status "Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    print_warning "Ollama is not installed locally. Installing..."
    
    # Install Ollama
    curl -fsSL https://ollama.ai/install.sh | sh
    
    if command -v ollama &> /dev/null; then
        print_success "Ollama installed successfully"
    else
        print_error "Failed to install Ollama. Please install manually from https://ollama.ai"
        exit 1
    fi
else
    print_success "Ollama is already installed"
fi

# Start Ollama service if not running
print_status "Starting Ollama service..."
if ! pgrep -f ollama &> /dev/null; then
    ollama serve &
    sleep 5
    print_success "Ollama service started"
else
    print_success "Ollama service is already running"
fi

# Pull required model
print_status "Pulling Llama 3.1 model (this may take a while)..."
if ollama list | grep -q "llama3.1"; then
    print_success "Llama 3.1 model already available"
else
    ollama pull llama3.1
    print_success "Llama 3.1 model downloaded"
fi

# Build Docker images
print_status "Building Docker images..."
cd docker
docker compose build
print_success "Docker images built"

print_success "Setup completed successfully!"
echo ""
echo "🎉 MCP Gateway MIA is ready to use!"
echo ""
echo "Next steps:"
echo "1. Start the services: ./start.sh"
echo "2. Run the demo: ./demo.sh"
echo "3. Access the gateway at: http://localhost:8000"
echo "4. View API docs at: http://localhost:8000/docs"
echo ""
echo "For monitoring (optional):"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "Logs are available in the ./logs directory"
EOF

chmod +x setup.sh

<task_progress>
- [x] Analyze current codebase structure
- [x] Create comprehensive todo list for MIA implementation
- [ ] Remove traditional security components
- [x] Create intent data models (IntentContract, ClientIntentDeclaration, ServerCapabilityDeclaration)
- [x] Implement IntentBroker for negotiation logic
- [x] Set up Ollama integration for LLM-powered intent analysis
- [ ] Create IntentSession for session management
- [x] Implement intent declaration system
- [x] Implement intent negotiation flow
- [x] Build example weather scenario
- [x] Create travel planner client example
- [x] Transform API endpoints for MIA
- [x] Set up local development environment
- [x] Create setup scripts and configuration
- [ ] Add monitoring and debugging features
- [ ] Create documentation and setup guides
- [ ] Test complete MIA flow end-to-end
</task_progress>
</write_to_file>
