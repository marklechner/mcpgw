#!/bin/bash

# MCP Gateway MIA Stop Script
# Stops all services gracefully

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

echo "🛑 Stopping MCP Gateway MIA Services"
echo "===================================="

# Stop Docker services
print_status "Stopping Docker services..."
cd docker

# Stop all services including monitoring
docker compose --profile monitoring down

# Remove volumes if --clean flag is provided
if [[ "$1" == "--clean" ]]; then
    print_status "Cleaning up volumes and data..."
    docker compose --profile monitoring down -v
    docker system prune -f
    print_success "Volumes and unused containers removed"
fi

cd ..

# Stop local Ollama service if running
print_status "Checking local Ollama service..."
if pgrep -f "ollama serve" > /dev/null; then
    print_status "Stopping local Ollama service..."
    pkill -f "ollama serve" || true
    sleep 2
    print_success "Local Ollama service stopped"
else
    print_status "Local Ollama service was not running"
fi

print_success "All services stopped successfully!"
echo ""
echo "🔧 Management Commands:"
echo "  • Restart services:    ./start.sh"
echo "  • Clean restart:       ./stop.sh --clean && ./start.sh"
echo "  • View stopped logs:   docker compose -f docker/docker-compose.yml logs"
echo "  • Remove everything:   ./stop.sh --clean"
echo ""

if [[ "$1" == "--clean" ]]; then
    print_warning "Clean stop completed - all data and volumes removed"
    echo "Next start will be completely fresh"
else
    print_status "Standard stop completed - data preserved"
    echo "Use './stop.sh --clean' to remove all data and start fresh"
fi
