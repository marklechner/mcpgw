#!/bin/bash

# MCP Gateway MIA Start Script
# Starts all services for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo "🚀 Starting MCP Gateway MIA Services"
echo "===================================="

# Check if setup has been run
if [ ! -f "config/mia_config.yml" ]; then
    print_error "Setup not completed. Please run ./setup.sh first."
    exit 1
fi

# Start Ollama service locally if not running
print_status "Checking Ollama service..."
if ! pgrep -f ollama &> /dev/null; then
    print_status "Starting Ollama service..."
    ollama serve &
    sleep 5
    print_success "Ollama service started"
else
    print_success "Ollama service is already running"
fi

# Verify Ollama model is available
print_status "Verifying Llama 3.1 model..."
if ollama list | grep -q "llama3.1"; then
    print_success "Llama 3.1 model is available"
else
    print_warning "Llama 3.1 model not found. Pulling model..."
    ollama pull llama3.1
    print_success "Llama 3.1 model downloaded"
fi

# Start Docker services
print_status "Starting Docker services..."
cd docker

# Start core services (gateway, weather server) - using local Ollama
docker compose up -d mia-gateway weather-server

print_status "Waiting for services to be healthy..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null; then
    print_success "✅ Ollama service is healthy"
else
    print_warning "⚠️  Ollama service may not be ready yet"
fi

# Check MIA Gateway
if curl -s http://localhost:8000/health > /dev/null; then
    print_success "✅ MIA Gateway is healthy"
else
    print_warning "⚠️  MIA Gateway may not be ready yet"
fi

# Check Weather Server
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    print_success "✅ Weather Server is healthy"
else
    print_warning "⚠️  Weather Server may not be ready yet (this is expected for demo)"
fi

cd ..

print_success "Core services started successfully!"
echo ""
echo "🌐 Service URLs:"
echo "  • MIA Gateway:     http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Gateway Health:  http://localhost:8000/health"
echo "  • Gateway Status:  http://localhost:8000/status"
echo "  • Ollama API:      http://localhost:11434"
echo ""
echo "📊 Optional Monitoring (run with --monitoring flag):"
echo "  • Prometheus:      http://localhost:9090"
echo "  • Grafana:         http://localhost:3000 (admin/admin)"
echo ""
echo "🔧 Management Commands:"
echo "  • View logs:       docker compose -f docker/docker-compose.yml logs -f"
echo "  • Stop services:   ./stop.sh"
echo "  • Run demo:        ./demo.sh"
echo ""

# Check for monitoring flag
if [[ "$1" == "--monitoring" ]]; then
    print_status "Starting monitoring services..."
    cd docker
    docker compose --profile monitoring up -d prometheus grafana
    cd ..
    print_success "Monitoring services started!"
    echo "  • Prometheus:      http://localhost:9090"
    echo "  • Grafana:         http://localhost:3000 (admin/admin)"
    echo ""
fi

# Check for demo flag
if [[ "$1" == "--demo" ]] || [[ "$2" == "--demo" ]]; then
    print_status "Starting demo client..."
    sleep 5  # Give services time to fully start
    ./demo.sh
fi

print_success "All services are running! 🎉"
echo ""
echo "Next steps:"
echo "1. Run the demo: ./demo.sh"
echo "2. Explore the API at: http://localhost:8000/docs"
echo "3. Check service status: curl http://localhost:8000/status"
