"""
MIA Gateway - Intent-Aware MCP Gateway

FastAPI application implementing Mutual Intent Agreement (MIA) for MCP protocol security.
Replaces traditional permission-based security with intent-aware validation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..core.intent_broker import IntentBroker
from ..core.intent_contract import (
    ClientIntentDeclaration,
    ServerCapabilityDeclaration,
    IntentContract,
    IntentTransactionValidation
)
from ..llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# Request/Response Models for MIA API
class IntentDeclarationRequest(BaseModel):
    """Request to declare client intent"""
    purpose: str = Field(..., description="Clear statement of intended purpose")
    data_requirements: List[str] = Field(..., description="Types of data needed")
    constraints: List[str] = Field(default_factory=list, description="Self-imposed constraints")
    duration: Optional[int] = Field(None, description="Session duration in minutes")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class CapabilityRegistrationRequest(BaseModel):
    """Request to register server capability"""
    server_name: str = Field(..., description="Unique server identifier")
    provides: List[str] = Field(..., description="Data/services provided")
    boundaries: List[str] = Field(..., description="Server boundaries and limitations")
    rate_limits: Dict[str, int] = Field(default_factory=dict, description="Rate limiting constraints")
    data_sensitivity: str = Field("public", description="Data sensitivity level")
    supported_operations: List[str] = Field(..., description="Supported operation types")

class IntentNegotiationRequest(BaseModel):
    """Request to negotiate intent contract"""
    client_intent_id: str = Field(..., description="Client intent declaration ID")
    server_capability_id: str = Field(..., description="Server capability registration ID")
    additional_constraints: Optional[List[str]] = Field(None, description="Additional constraints")

class MCPRequest(BaseModel):
    """MCP request with intent context"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPResponse(BaseModel):
    """MCP response"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class IntentMCPRequest(BaseModel):
    """MCP request with intent validation"""
    contract_id: str = Field(..., description="Intent contract ID")
    server_name: str = Field(..., description="Target MCP server")
    request: MCPRequest = Field(..., description="MCP request payload")

# Global instances
intent_broker: Optional[IntentBroker] = None
ollama_client: Optional[OllamaClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global intent_broker, ollama_client
    
    logger.info("Starting MIA Gateway")
    
    # Initialize Ollama client with environment URL
    import os
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_client = OllamaClient(base_url=ollama_url)
    
    # Check Ollama availability
    try:
        if await ollama_client.health_check():
            logger.info("Ollama connection successful")
        else:
            logger.warning("Ollama model not available - intent analysis will be limited")
    except Exception as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        logger.warning("Continuing without Ollama - intent analysis will be mocked")
    
    # Initialize intent broker
    intent_broker = IntentBroker(ollama_client)
    
    # Register example server capability for demo
    demo_capability = ServerCapabilityDeclaration(
        provides=["weather_data", "location_weather", "forecast_data"],
        boundaries=["public_data_only", "no_personal_info", "rate_limited"],
        rate_limits={"requests_per_minute": 60, "data_points_per_hour": 1000},
        data_sensitivity="public",
        supported_operations=["read", "query", "aggregate"]
    )
    
    capability_id = await intent_broker.register_server_capability(demo_capability)
    logger.info(f"Demo weather server capability registered: {capability_id}")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Cleanup
    cleanup_task.cancel()
    if ollama_client:
        await ollama_client.__aexit__(None, None, None)
    
    logger.info("MIA Gateway shutdown complete")

async def periodic_cleanup():
    """Periodic cleanup of expired contracts"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            if intent_broker:
                expired_count = await intent_broker.cleanup_expired_contracts()
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired contracts")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")

# FastAPI app
app = FastAPI(
    title="MCP Gateway - Mutual Intent Agreement",
    description="Intent-aware security layer for MCP protocols",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Health and status endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ollama_status = "unknown"
    if ollama_client:
        try:
            ollama_status = "available" if await ollama_client.health_check() else "unavailable"
        except:
            ollama_status = "error"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mia_enabled": True,
        "ollama_status": ollama_status,
        "broker_stats": intent_broker.get_broker_stats() if intent_broker else {}
    }

@app.get("/status")
async def get_status():
    """Get detailed system status"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    return {
        "system": "MIA Gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "broker_stats": intent_broker.get_broker_stats(),
        "active_contracts": len(intent_broker.get_active_contracts()),
        "ollama_available": await ollama_client.health_check() if ollama_client else False
    }

# Phase 1: Intent Declaration and Capability Registration
@app.post("/intent/declare")
async def declare_intent(request: IntentDeclarationRequest) -> Dict[str, Any]:
    """Phase 1: Client declares their intent"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    # Create intent declaration
    intent = ClientIntentDeclaration(
        purpose=request.purpose,
        data_requirements=request.data_requirements,
        constraints=request.constraints,
        duration=request.duration,
        context=request.context
    )
    
    try:
        intent_id = await intent_broker.declare_client_intent(intent)
        
        return {
            "intent_id": intent_id,
            "client_id": intent.client_id,
            "status": "declared",
            "message": "Intent successfully declared",
            "declared_at": intent.declared_at.isoformat(),
            "purpose": intent.purpose
        }
    
    except Exception as e:
        logger.error(f"Intent declaration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intent declaration failed: {str(e)}")

@app.post("/capability/register")
async def register_capability(request: CapabilityRegistrationRequest) -> Dict[str, Any]:
    """Phase 1: Server registers its capabilities"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    # Create capability declaration
    capability = ServerCapabilityDeclaration(
        provides=request.provides,
        boundaries=request.boundaries,
        rate_limits=request.rate_limits,
        data_sensitivity=request.data_sensitivity,
        supported_operations=request.supported_operations
    )
    
    try:
        capability_id = await intent_broker.register_server_capability(capability)
        
        return {
            "capability_id": capability_id,
            "server_id": capability.server_id,
            "server_name": request.server_name,
            "status": "registered",
            "message": "Capability successfully registered",
            "registered_at": capability.registered_at.isoformat(),
            "provides": capability.provides
        }
    
    except Exception as e:
        logger.error(f"Capability registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Capability registration failed: {str(e)}")

# Phase 2: Intent Negotiation
@app.post("/intent/negotiate")
async def negotiate_contract(request: IntentNegotiationRequest) -> Dict[str, Any]:
    """Phase 2: Negotiate intent contract between client and server"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    try:
        contract = await intent_broker.negotiate_intent_contract(
            client_intent_id=request.client_intent_id,
            server_capability_id=request.server_capability_id,
            additional_constraints=request.additional_constraints
        )
        
        return {
            "contract_id": contract.contract_id,
            "status": "active" if contract.is_active else "inactive",
            "agreed_purpose": contract.agreed_purpose,
            "constraints": contract.constraints,
            "allowed_operations": contract.allowed_operations,
            "data_access_scope": contract.data_access_scope,
            "rate_limits": contract.rate_limits,
            "created_at": contract.created_at.isoformat(),
            "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
            "compatibility_analysis": contract.compatibility_result.to_dict() if contract.compatibility_result else None
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Contract negotiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contract negotiation failed: {str(e)}")

# Phase 3: Intent-Validated MCP Requests
@app.post("/mcp/request")
async def process_mcp_request(request: IntentMCPRequest) -> MCPResponse:
    """Phase 3: Process MCP request with intent validation"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    # Validate transaction against intent contract
    validation = await intent_broker.validate_transaction(
        contract_id=request.contract_id,
        request_data=request.request.dict()
    )
    
    # Check if transaction is allowed
    if validation.suggested_action == "deny":
        return MCPResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": "Intent validation failed",
                "data": {
                    "validation_result": validation.validation_result.value,
                    "reasons": validation.validation_reasons,
                    "risk_factors": validation.risk_factors,
                    "intent_alignment_score": validation.intent_alignment_score
                }
            },
            id=request.request.id
        )
    
    try:
        # Simulate MCP server communication
        # In a real implementation, this would forward to actual MCP servers
        response_data = await simulate_mcp_server_response(request.server_name, request.request)
        
        # Validate response against intent
        response_validation = await intent_broker.validate_transaction(
            contract_id=request.contract_id,
            request_data=request.request.dict(),
            response_data=response_data.dict() if response_data else None
        )
        
        # Log validation results
        logger.info(f"Request validation: {validation.validation_result.value}")
        logger.info(f"Response validation: {response_validation.validation_result.value}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"MCP request processing failed: {e}")
        return MCPResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": "Internal error",
                "data": {"details": str(e)}
            },
            id=request.request.id
        )

async def simulate_mcp_server_response(server_name: str, request: MCPRequest) -> MCPResponse:
    """Simulate MCP server response for demo purposes"""
    
    # Simulate processing delay
    await asyncio.sleep(0.1)
    
    if request.method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"}
                        },
                        "required": ["location"]
                    }
                },
                {
                    "name": "get_forecast",
                    "description": "Get weather forecast for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"},
                            "days": {"type": "integer", "description": "Number of days", "default": 5}
                        },
                        "required": ["location"]
                    }
                }
            ]
        }
    elif request.method == "tools/call":
        tool_name = request.params.get("name", "") if request.params else ""
        arguments = request.params.get("arguments", {}) if request.params else {}
        
        if tool_name == "get_weather":
            location = arguments.get("location", "Unknown")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Current weather in {location}: 22°C, partly cloudy with light winds. Humidity: 65%. UV Index: 6 (High). Good conditions for travel planning."
                    }
                ]
            }
        elif tool_name == "get_forecast":
            location = arguments.get("location", "Unknown")
            days = arguments.get("days", 5)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"{days}-day forecast for {location}: Mostly sunny with temperatures ranging from 18-25°C. Light rain expected on day 3. Excellent conditions for outdoor travel activities."
                    }
                ]
            }
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    else:
        result = {"message": f"Processed {request.method}"}
    
    return MCPResponse(
        jsonrpc="2.0",
        result=result,
        id=request.id
    )

# Contract Management Endpoints
@app.get("/intent/capabilities")
async def list_capabilities() -> Dict[str, Any]:
    """List all registered server capabilities"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    capabilities = []
    for cap_id, capability in intent_broker.server_capabilities.items():
        capabilities.append({
            "capability_id": cap_id,
            "server_id": capability.server_id,
            "provides": capability.provides,
            "boundaries": capability.boundaries,
            "data_sensitivity": capability.data_sensitivity,
            "registered_at": capability.registered_at.isoformat()
        })
    
    return {
        "total_capabilities": len(capabilities),
        "capabilities": capabilities
    }

@app.get("/intent/contracts")
async def list_contracts() -> Dict[str, Any]:
    """List all active intent contracts"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    active_contracts = intent_broker.get_active_contracts()
    
    return {
        "active_contracts": len(active_contracts),
        "contracts": [
            {
                "contract_id": contract.contract_id,
                "agreed_purpose": contract.agreed_purpose,
                "created_at": contract.created_at.isoformat(),
                "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
                "transaction_count": contract.transaction_count,
                "success_rate": contract.get_success_rate(),
                "violation_count": contract.violation_count
            }
            for contract in active_contracts
        ]
    }

@app.get("/intent/contracts/{contract_id}")
async def get_contract_details(contract_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific contract"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    stats = intent_broker.get_contract_stats(contract_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    
    return stats

@app.get("/intent/violations")
async def get_violations() -> Dict[str, Any]:
    """Get intent violations across all contracts"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    violations = []
    for contract in intent_broker.active_contracts.values():
        if contract.violation_count > 0:
            violations.append({
                "contract_id": contract.contract_id,
                "agreed_purpose": contract.agreed_purpose,
                "violation_count": contract.violation_count,
                "success_rate": contract.get_success_rate(),
                "is_active": contract.is_active
            })
    
    return {
        "total_violations": sum(v["violation_count"] for v in violations),
        "contracts_with_violations": len(violations),
        "violations": violations
    }

@app.post("/intent/drift-analysis/{contract_id}")
async def analyze_drift(contract_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
    """Analyze intent drift for a specific contract"""
    if not intent_broker:
        raise HTTPException(status_code=503, detail="Intent broker not initialized")
    
    drift_analysis = await intent_broker.analyze_intent_drift(contract_id, time_window_hours)
    
    if "error" in drift_analysis:
        raise HTTPException(status_code=404, detail=drift_analysis["error"])
    
    return drift_analysis

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MIA Gateway - Intent-Aware MCP Security")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting MIA Gateway on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.mcpgw.gateway.mia_gateway:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()
