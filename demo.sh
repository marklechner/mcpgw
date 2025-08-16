#!/bin/bash

# MCP Gateway MIA Demo Script
# Demonstrates the complete Mutual Intent Agreement flow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

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

print_demo() {
    echo -e "${CYAN}[DEMO]${NC} $1"
}

# Check if services are running
check_services() {
    print_status "Checking if services are running..."
    
    if ! curl -s http://localhost:8000/health > /dev/null; then
        print_error "MIA Gateway is not running. Please run ./start.sh first."
        exit 1
    fi
    
    if ! curl -s http://localhost:11434/api/tags > /dev/null; then
        print_error "Ollama is not running. Please run ./start.sh first."
        exit 1
    fi
    
    print_success "All services are running"
}

# Demo 1: Basic MIA Flow
demo_basic_mia_flow() {
    print_header "🔐 Demo 1: Basic Mutual Intent Agreement Flow"
    echo "=============================================="
    
    print_demo "This demo shows the 3-phase MIA process:"
    print_demo "1. Intent Declaration - Client declares purpose"
    print_demo "2. Capability Registration - Server declares boundaries"  
    print_demo "3. Contract Negotiation - LLM analyzes compatibility"
    echo ""
    
    # Phase 1: Declare Intent
    print_status "Phase 1: Declaring client intent for travel planning..."
    
    INTENT_RESPONSE=$(curl -s -X POST http://localhost:8000/intent/declare \
        -H "Content-Type: application/json" \
        -d '{
            "purpose": "I need weather data to help users plan their travel itineraries and provide weather-based travel recommendations",
            "data_requirements": ["current_weather_conditions", "weather_forecasts", "location_based_weather"],
            "constraints": ["read_only_access", "no_personal_data_storage", "travel_planning_context_only"],
            "duration": 60,
            "context": {
                "use_case": "travel_planning_assistant",
                "user_facing": true,
                "data_retention": "none"
            }
        }')
    
    INTENT_ID=$(echo $INTENT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['intent_id'])")
    print_success "Intent declared successfully!"
    print_demo "Intent ID: $INTENT_ID"
    echo ""
    
    # Phase 2: Register Server Capability (already done at startup)
    print_status "Phase 2: Server capability already registered at startup"
    print_demo "Weather server provides: weather_data, forecasts, travel_advice"
    print_demo "Server boundaries: public_data_only, no_personal_tracking"
    echo ""
    
    # Phase 3: Negotiate Contract
    print_status "Phase 3: Negotiating intent contract..."
    print_demo "LLM analyzing compatibility between client intent and server capability..."
    
    # Get the actual registered server capability ID
    print_status "Finding registered server capability..."
    
    CAPABILITIES_RESPONSE=$(curl -s http://localhost:8000/intent/capabilities)
    SERVER_CAPABILITY_ID=$(echo $CAPABILITIES_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['capabilities'][0]['capability_id']) if data['capabilities'] else print('none')")
    
    if [ "$SERVER_CAPABILITY_ID" = "none" ]; then
        print_error "No server capabilities found"
        return 1
    fi
    
    print_demo "Using server capability ID: $SERVER_CAPABILITY_ID"
    
    CONTRACT_RESPONSE=$(curl -s -X POST http://localhost:8000/intent/negotiate \
        -H "Content-Type: application/json" \
        -d "{
            \"client_intent_id\": \"$INTENT_ID\",
            \"server_capability_id\": \"$SERVER_CAPABILITY_ID\",
            \"additional_constraints\": [\"demo_mode_enabled\"]
        }")
    
    CONTRACT_ID=$(echo $CONTRACT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['contract_id'])")
    CONTRACT_STATUS=$(echo $CONTRACT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
    
    if [ "$CONTRACT_STATUS" = "active" ]; then
        print_success "Contract negotiated successfully!"
        print_demo "Contract ID: $CONTRACT_ID"
        print_demo "Status: $CONTRACT_STATUS"
        echo ""
    else
        print_error "Contract negotiation failed or requires manual approval"
        echo "Response: $CONTRACT_RESPONSE"
        return 1
    fi
    
    return 0
}

# Demo 2: Intent-Validated Requests
demo_intent_validated_requests() {
    print_header "🌤️  Demo 2: Intent-Validated MCP Requests"
    echo "=========================================="
    
    print_demo "Now making MCP requests that are validated against the intent contract"
    echo ""
    
    # Get current weather for Paris
    print_status "Requesting current weather for Paris (aligned with travel planning intent)..."
    
    WEATHER_RESPONSE=$(curl -s -X POST http://localhost:8000/mcp/request \
        -H "Content-Type: application/json" \
        -d "{
            \"contract_id\": \"$CONTRACT_ID\",
            \"server_name\": \"weather-server\",
            \"request\": {
                \"jsonrpc\": \"2.0\",
                \"method\": \"tools/call\",
                \"params\": {
                    \"name\": \"get_current_weather\",
                    \"arguments\": {
                        \"location\": \"Paris\"
                    }
                },
                \"id\": \"weather-demo-1\"
            }
        }")
    
    if echo $WEATHER_RESPONSE | grep -q '"result"'; then
        print_success "Weather request validated and processed!"
        WEATHER_TEXT=$(echo $WEATHER_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'result' in data:
        if 'content' in data['result'] and len(data['result']['content']) > 0:
            print(data['result']['content'][0].get('text', 'Weather data retrieved')[:100] + '...')
        else:
            print('Weather data retrieved successfully')
    else:
        print('Response received')
except:
    print('Weather data processed')
")
        print_demo "Weather data: $WEATHER_TEXT"
    else
        print_warning "Weather request may have been blocked or failed"
        echo "Response: $WEATHER_RESPONSE"
    fi
    echo ""
    
    # Get travel forecast
    print_status "Requesting 5-day forecast for London (travel planning context)..."
    
    FORECAST_RESPONSE=$(curl -s -X POST http://localhost:8000/mcp/request \
        -H "Content-Type: application/json" \
        -d "{
            \"contract_id\": \"$CONTRACT_ID\",
            \"server_name\": \"weather-server\",
            \"request\": {
                \"jsonrpc\": \"2.0\",
                \"method\": \"tools/call\",
                \"params\": {
                    \"name\": \"get_weather_forecast\",
                    \"arguments\": {
                        \"location\": \"London\",
                        \"days\": 5
                    }
                },
                \"id\": \"forecast-demo-1\"
            }
        }")
    
    if echo $FORECAST_RESPONSE | grep -q '"result"'; then
        print_success "Forecast request validated and processed!"
        print_demo "5-day forecast retrieved for London"
    else
        print_warning "Forecast request may have been blocked or failed"
    fi
    echo ""
}

# Demo 3: Intent Violation Detection
demo_intent_violation() {
    print_header "🚨 Demo 3: Intent Violation Detection"
    echo "====================================="
    
    print_demo "Attempting a request that violates the travel planning intent..."
    print_demo "This should be detected and blocked by the MIA system"
    echo ""
    
    print_status "Attempting to access personal location history (violates intent)..."
    
    VIOLATION_RESPONSE=$(curl -s -X POST http://localhost:8000/mcp/request \
        -H "Content-Type: application/json" \
        -d "{
            \"contract_id\": \"$CONTRACT_ID\",
            \"server_name\": \"weather-server\",
            \"request\": {
                \"jsonrpc\": \"2.0\",
                \"method\": \"tools/call\",
                \"params\": {
                    \"name\": \"get_personal_location_history\",
                    \"arguments\": {
                        \"user_id\": \"12345\",
                        \"include_private_data\": true
                    }
                },
                \"id\": \"violation-demo-1\"
            }
        }")
    
    if echo $VIOLATION_RESPONSE | grep -q '"error"'; then
        print_success "Intent violation correctly detected and blocked!"
        ERROR_MSG=$(echo $VIOLATION_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['error']['message'])")
        print_demo "Error message: $ERROR_MSG"
        
        if echo $VIOLATION_RESPONSE | grep -q 'validation_result'; then
            VALIDATION_RESULT=$(echo $VIOLATION_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['error']['data']['validation_result'])")
            print_demo "Validation result: $VALIDATION_RESULT"
        fi
    else
        print_error "Intent violation was NOT detected - this is a problem!"
        echo "Response: $VIOLATION_RESPONSE"
    fi
    echo ""
}

# Demo 4: Contract Statistics and Monitoring
demo_contract_monitoring() {
    print_header "📊 Demo 4: Contract Statistics and Monitoring"
    echo "=============================================="
    
    print_demo "Viewing contract statistics and system monitoring data"
    echo ""
    
    # Get contract details
    print_status "Retrieving contract statistics..."
    
    CONTRACT_STATS=$(curl -s http://localhost:8000/intent/contracts/$CONTRACT_ID)
    
    if echo $CONTRACT_STATS | grep -q 'transaction_count'; then
        TRANSACTION_COUNT=$(echo $CONTRACT_STATS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['transaction_count'])")
        SUCCESS_RATE=$(echo $CONTRACT_STATS | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['success_rate']:.1%}\")")
        VIOLATION_COUNT=$(echo $CONTRACT_STATS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['violation_count'])")
        
        print_success "Contract statistics retrieved!"
        print_demo "Transactions processed: $TRANSACTION_COUNT"
        print_demo "Success rate: $SUCCESS_RATE"
        print_demo "Violations detected: $VIOLATION_COUNT"
    else
        print_warning "Could not retrieve contract statistics"
    fi
    echo ""
    
    # Get system status
    print_status "Retrieving system status..."
    
    SYSTEM_STATUS=$(curl -s http://localhost:8000/status)
    
    if echo $SYSTEM_STATUS | grep -q 'broker_stats'; then
        ACTIVE_CONTRACTS=$(echo $SYSTEM_STATUS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['active_contracts'])")
        OLLAMA_STATUS=$(echo $SYSTEM_STATUS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['ollama_available'])")
        
        print_success "System status retrieved!"
        print_demo "Active contracts: $ACTIVE_CONTRACTS"
        print_demo "Ollama available: $OLLAMA_STATUS"
    else
        print_warning "Could not retrieve system status"
    fi
    echo ""
}

# Demo 5: Python Client Example
demo_python_client() {
    print_header "🐍 Demo 5: Python Client Example"
    echo "================================="
    
    print_demo "Running the Python travel planner client example..."
    print_demo "This demonstrates a complete application using MIA"
    echo ""
    
    print_status "Activating virtual environment and running client..."
    
    # Check if virtual environment exists
    if [ -d "venv" ]; then
        source venv/bin/activate
        
        # Run the Python client demo
        if python3 -m src.mcpgw.examples.portfolio_client.travel_planner_client; then
            print_success "Python client demo completed successfully!"
        else
            print_warning "Python client demo encountered issues (this may be expected)"
        fi
    else
        print_warning "Virtual environment not found. Skipping Python client demo."
        print_demo "Run ./setup.sh to create the virtual environment"
    fi
    echo ""
}

# Main demo execution
main() {
    echo "🎭 MCP Gateway MIA - Complete Demonstration"
    echo "==========================================="
    echo ""
    print_demo "This demo showcases the world's first intent-aware MCP security layer"
    print_demo "Instead of 'can this client access this tool?', we ask:"
    print_demo "'does this transaction serve the agreed intent between client and server?'"
    echo ""
    
    # Check services
    check_services
    echo ""
    
    # Run demos
    if demo_basic_mia_flow; then
        demo_intent_validated_requests
        demo_intent_violation
        demo_contract_monitoring
        
        # Ask if user wants to run Python client demo
        echo ""
        read -p "Run Python client demo? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            demo_python_client
        fi
    else
        print_error "Basic MIA flow failed. Skipping remaining demos."
        exit 1
    fi
    
    # Final summary
    print_header "🎉 Demo Complete!"
    echo "================="
    echo ""
    print_success "You've seen the complete Mutual Intent Agreement flow:"
    print_demo "✅ Intent declaration and capability registration"
    print_demo "✅ LLM-powered compatibility analysis"
    print_demo "✅ Intent-validated transaction processing"
    print_demo "✅ Real-time violation detection"
    print_demo "✅ Contract monitoring and statistics"
    echo ""
    print_demo "Key Benefits of MIA:"
    print_demo "• Semantic understanding of client intentions"
    print_demo "• Dynamic security based on declared purpose"
    print_demo "• Real-time intent drift detection"
    print_demo "• Transparent and auditable security decisions"
    print_demo "• No static permission lists to maintain"
    echo ""
    print_demo "Next steps:"
    print_demo "• Explore the API documentation: http://localhost:8000/docs"
    print_demo "• View contract details: http://localhost:8000/intent/contracts"
    print_demo "• Check system status: http://localhost:8000/status"
    print_demo "• Review logs: docker compose -f docker/docker-compose.yml logs"
    echo ""
    print_success "MIA demo completed successfully! 🚀"
}

# Run the demo
main "$@"
