#!/usr/bin/env python3
"""
FastAPI MCP Gateway - A lightweight security-focused gateway for MCP servers

This gateway acts as an intermediary between MCP clients and servers, providing:
- Authentication and authorization
- Request/response validation and sanitization
- Rate limiting and resource quotas
- Policy enforcement and security controls
- Audit logging and monitoring
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import re

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security models
class SecurityPolicy(BaseModel):
    """Security policy configuration for MCP server access"""
    allowed_tools: Set[str] = Field(default_factory=set, description="Allowed tool names")
    allowed_resources: Set[str] = Field(default_factory=set, description="Allowed resource patterns")
    max_requests_per_minute: int = Field(default=60, description="Rate limit per minute")
    max_request_size: int = Field(default=1024*1024, description="Max request size in bytes")
    require_auth: bool = Field(default=True, description="Require authentication")
    allowed_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")
    sandbox_mode: bool = Field(default=True, description="Enable sandboxing")

class ClientConfig(BaseModel):
    """Client configuration and credentials"""
    client_id: str
    client_secret: str
    policy: SecurityPolicy
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_active: bool = True

# Request/Response models
class MCPRequest(BaseModel):
    """Standardized MCP request format"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPResponse(BaseModel):
    """Standardized MCP response format"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class GatewayRequest(BaseModel):
    """Gateway request wrapper"""
    server_name: str = Field(..., description="Target MCP server name")
    request: MCPRequest = Field(..., description="MCP request payload")

# Rate limiting
@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting"""
    capacity: int
    tokens: float = field(default_factory=lambda: 0)
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens from bucket"""
        now = time.time()
        # Refill tokens based on time elapsed
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.capacity / 60))  # 1 token per second
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class SecurityManager:
    """Manages security policies and validation"""
    
    def __init__(self):
        self.clients: Dict[str, ClientConfig] = {}
        self.rate_limits: Dict[str, RateLimitBucket] = {}
        self.audit_log: List[Dict[str, Any]] = []
        
    def register_client(self, client_config: ClientConfig) -> str:
        """Register a new client with security policy"""
        client_token = self._generate_token(client_config.client_id)
        self.clients[client_token] = client_config
        self.rate_limits[client_token] = RateLimitBucket(
            capacity=client_config.policy.max_requests_per_minute
        )
        logger.info(f"Registered client: {client_config.client_id}")
        return client_token
    
    def validate_client(self, token: str) -> Optional[ClientConfig]:
        """Validate client token and return config"""
        client = self.clients.get(token)
        if client and client.is_active:
            client.last_used = datetime.utcnow()
            return client
        return None
    
    def check_rate_limit(self, token: str) -> bool:
        """Check if client is within rate limits"""
        bucket = self.rate_limits.get(token)
        return bucket.consume() if bucket else False
    
    def validate_request(self, client: ClientConfig, request: GatewayRequest) -> bool:
        """Validate request against client policy"""
        policy = client.policy
        
        # Check request size
        request_size = len(json.dumps(request.dict()).encode())
        if request_size > policy.max_request_size:
            logger.warning(f"Request size {request_size} exceeds limit {policy.max_request_size}")
            return False
        
        # Validate method against allowed tools/resources
        method = request.request.method
        if method.startswith("tools/"):
            tool_name = method.replace("tools/", "")
            if policy.allowed_tools and tool_name not in policy.allowed_tools:
                logger.warning(f"Tool {tool_name} not in allowed list")
                return False
        elif method.startswith("resources/"):
            resource_pattern = method.replace("resources/", "")
            if policy.allowed_resources and not any(
                re.match(pattern, resource_pattern) for pattern in policy.allowed_resources
            ):
                logger.warning(f"Resource {resource_pattern} not matching allowed patterns")
                return False
        
        return True
    
    def sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response to remove sensitive information"""
        # Remove potential sensitive fields
        sensitive_fields = ["password", "token", "key", "secret", "credential"]
        
        def clean_dict(obj):
            if isinstance(obj, dict):
                return {
                    k: clean_dict(v) for k, v in obj.items()
                    if not any(sensitive in k.lower() for sensitive in sensitive_fields)
                }
            elif isinstance(obj, list):
                return [clean_dict(item) for item in obj]
            return obj
        
        return clean_dict(response)
    
    def log_request(self, client_id: str, request: GatewayRequest, response: Optional[Dict], error: Optional[str]):
        """Log request for audit purposes"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client_id,
            "server_name": request.server_name,
            "method": request.request.method,
            "success": error is None,
            "error": error
        }
        self.audit_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def _generate_token(self, client_id: str) -> str:
        """Generate secure token for client"""
        return hashlib.sha256(f"{client_id}:{time.time()}".encode()).hexdigest()

class MCPServerManager:
    """Manages connections to MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.load_server_config()
    
    def load_server_config(self):
        """Load MCP server configurations"""
        # In a real implementation, this would load from configuration files
        # For now, we'll use a simple in-memory configuration
        self.servers = {
            "example-weather": {
                "command": "node",
                "args": ["/path/to/weather-server/build/index.js"],
                "env": {"OPENWEATHER_API_KEY": "your-api-key"},
                "enabled": True
            }
        }
    
    async def send_request(self, server_name: str, request: MCPRequest) -> MCPResponse:
        """Send request to MCP server (simplified implementation)"""
        if server_name not in self.servers:
            raise HTTPException(status_code=404, detail=f"Server {server_name} not found")
        
        server_config = self.servers[server_name]
        if not server_config.get("enabled", False):
            raise HTTPException(status_code=503, detail=f"Server {server_name} is disabled")
        
        # In a real implementation, this would establish a connection to the MCP server
        # and send the request via stdio or other transport
        # For this MVP, we'll return a mock response
        
        logger.info(f"Sending request to {server_name}: {request.method}")
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Mock response based on method
        if request.method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "Get current weather for a city",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string", "description": "City name"}
                            },
                            "required": ["city"]
                        }
                    }
                ]
            }
        elif request.method == "tools/call":
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Mock weather data for {request.params.get('arguments', {}).get('city', 'unknown city')}"
                    }
                ]
            }
        else:
            result = {"message": f"Processed {request.method}"}
        
        return MCPResponse(
            jsonrpc="2.0",
            result=result,
            id=request.id
        )

# Global instances
security_manager = SecurityManager()
server_manager = MCPServerManager()
security = HTTPBearer()

# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting MCP Gateway")
    
    # Register a default client for testing
    default_policy = SecurityPolicy(
        allowed_tools={"get_weather", "get_forecast"},
        allowed_resources={"weather://*"},
        max_requests_per_minute=100,
        require_auth=True,
        sandbox_mode=True
    )
    default_client = ClientConfig(
        client_id="test-client",
        client_secret="test-secret",
        policy=default_policy
    )
    token = security_manager.register_client(default_client)
    logger.info(f"Default client registered with token: {token}")
    
    yield
    
    logger.info("Shutting down MCP Gateway")

app = FastAPI(
    title="MCP Gateway",
    description="A lightweight security-focused gateway for MCP servers",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on client policies
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Authentication dependency
async def get_current_client(credentials: HTTPAuthorizationCredentials = Depends(security)) -> ClientConfig:
    """Validate client authentication"""
    client = security_manager.validate_client(credentials.credentials)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    if not security_manager.check_rate_limit(credentials.credentials):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return client

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }

@app.get("/servers")
async def list_servers(client: ClientConfig = Depends(get_current_client)):
    """List available MCP servers"""
    return {
        "servers": list(server_manager.servers.keys()),
        "client_id": client.client_id
    }

@app.post("/mcp/request")
async def proxy_mcp_request(
    gateway_request: GatewayRequest,
    client: ClientConfig = Depends(get_current_client)
) -> MCPResponse:
    """Proxy MCP request to target server with security validation"""
    
    # Validate request against client policy
    if not security_manager.validate_request(client, gateway_request):
        security_manager.log_request(client.client_id, gateway_request, None, "Policy violation")
        raise HTTPException(status_code=403, detail="Request violates security policy")
    
    try:
        # Send request to MCP server
        response = await server_manager.send_request(
            gateway_request.server_name,
            gateway_request.request
        )
        
        # Sanitize response
        if response.result:
            response.result = security_manager.sanitize_response(response.result)
        
        # Log successful request
        security_manager.log_request(client.client_id, gateway_request, response.dict(), None)
        
        return response
        
    except Exception as e:
        error_msg = str(e)
        security_manager.log_request(client.client_id, gateway_request, None, error_msg)
        logger.error(f"Error processing request: {error_msg}")
        
        return MCPResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": "Internal error",
                "data": {"details": error_msg}
            },
            id=gateway_request.request.id
        )

@app.get("/audit/logs")
async def get_audit_logs(client: ClientConfig = Depends(get_current_client)):
    """Get audit logs (admin only)"""
    # In a real implementation, you'd check for admin privileges
    return {
        "logs": security_manager.audit_log[-100:],  # Last 100 entries
        "total_entries": len(security_manager.audit_log)
    }

@app.post("/admin/register-client")
async def register_client(client_config: ClientConfig):
    """Register a new client (admin endpoint)"""
    # In a real implementation, this would require admin authentication
    token = security_manager.register_client(client_config)
    return {
        "client_id": client_config.client_id,
        "token": token,
        "message": "Client registered successfully"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
