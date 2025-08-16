# MCP Gateway

A lightweight, security-focused FastAPI gateway for Model Context Protocol (MCP) servers. This gateway acts as an intermediary between MCP clients and servers, providing authentication, authorization, rate limiting, request validation, and audit logging.

## Features

### Security
- **Authentication & Authorization**: Token-based authentication with configurable client policies
- **Request Validation**: Validates requests against allowed tools and resources
- **Response Sanitization**: Removes sensitive information from responses
- **Rate Limiting**: Token bucket algorithm for request rate limiting
- **Audit Logging**: Comprehensive logging of all requests and responses
- **Sandbox Mode**: Isolates MCP server execution (planned enhancement)

### Gateway Functionality
- **Request Proxying**: Forwards validated requests to appropriate MCP servers
- **Policy Enforcement**: Enforces client-specific security policies
- **Error Handling**: Graceful error handling with proper HTTP status codes
- **CORS Support**: Configurable CORS policies for web clients

### Monitoring & Management
- **Health Checks**: Built-in health check endpoint
- **Metrics**: Request metrics and performance monitoring (planned)
- **Admin API**: Client registration and management endpoints

## Quick Start

### Installation

1. Clone or create the project directory:
```bash
mkdir mcpgw && cd mcpgw
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the gateway:
```bash
python main.py
```

The gateway will start on `http://localhost:8000`

### Basic Usage

1. **Health Check**:
```bash
curl http://localhost:8000/health
```

2. **Register a Client** (for testing):
```bash
curl -X POST http://localhost:8000/admin/register-client \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "my-client",
    "client_secret": "my-secret",
    "policy": {
      "allowed_tools": ["get_weather"],
      "allowed_resources": ["weather://*"],
      "max_requests_per_minute": 100,
      "require_auth": true,
      "sandbox_mode": true
    }
  }'
```

3. **Make MCP Request**:
```bash
curl -X POST http://localhost:8000/mcp/request \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "example-weather",
    "request": {
      "jsonrpc": "2.0",
      "method": "tools/list",
      "id": "1"
    }
  }'
```

## Configuration

### Security Policies

Each client can have a custom security policy:

```python
{
  "allowed_tools": ["tool1", "tool2"],           # Allowed tool names
  "allowed_resources": ["resource://*"],         # Resource patterns (regex)
  "max_requests_per_minute": 60,                # Rate limit
  "max_request_size": 1048576,                  # Max request size (bytes)
  "require_auth": true,                         # Require authentication
  "allowed_origins": ["https://example.com"],   # CORS origins
  "sandbox_mode": true                          # Enable sandboxing
}
```

### MCP Server Configuration

Configure MCP servers in the `MCPServerManager.load_server_config()` method or via configuration files:

```python
{
  "server-name": {
    "command": "node",
    "args": ["/path/to/server/build/index.js"],
    "env": {"API_KEY": "your-key"},
    "enabled": true
  }
}
```

## API Endpoints

### Public Endpoints

- `GET /health` - Health check
- `POST /admin/register-client` - Register new client (admin only)

### Authenticated Endpoints

- `GET /servers` - List available MCP servers
- `POST /mcp/request` - Proxy MCP request to server
- `GET /audit/logs` - Get audit logs

## Security Features

### Authentication
- Bearer token authentication
- Client-specific tokens with policies
- Token validation and expiration

### Request Validation
- Method validation against allowed tools/resources
- Request size limits
- Input sanitization
- Policy enforcement

### Rate Limiting
- Token bucket algorithm
- Per-client rate limits
- Configurable limits per security policy

### Audit Logging
- All requests logged with timestamps
- Client identification
- Success/failure tracking
- Error details

### Response Sanitization
- Removes sensitive fields (passwords, tokens, keys, secrets)
- Recursive sanitization of nested objects
- Configurable sensitive field patterns

## Architecture

```
Client → Gateway → MCP Server
   ↓        ↓         ↓
Auth    Validation  Response
Rate    Logging     Sanitization
Limit   Policy      Error Handling
        Enforcement
```

### Components

1. **SecurityManager**: Handles authentication, authorization, and policy enforcement
2. **MCPServerManager**: Manages connections and communication with MCP servers
3. **RateLimitBucket**: Implements token bucket rate limiting
4. **FastAPI App**: HTTP server with middleware and endpoints

## Future Enhancements

### Security
- [ ] JWT token support
- [ ] OAuth2 integration
- [ ] Role-based access control (RBAC)
- [ ] Request signing and verification
- [ ] IP whitelisting/blacklisting
- [ ] Advanced sandboxing with containers

### Functionality
- [ ] WebSocket support for real-time communication
- [ ] Request/response caching
- [ ] Load balancing across multiple MCP servers
- [ ] Circuit breaker pattern for fault tolerance
- [ ] Request transformation and middleware

### Monitoring
- [ ] Prometheus metrics
- [ ] Distributed tracing
- [ ] Performance monitoring
- [ ] Alert system
- [ ] Dashboard UI

### Storage
- [ ] Redis backend for rate limiting
- [ ] Database storage for audit logs
- [ ] Configuration management UI
- [ ] Client management dashboard

## Development

### Running in Development Mode

```bash
python main.py
```

The server will reload automatically on code changes.

### Testing

Create test clients and policies:

```python
# Example test client
test_policy = SecurityPolicy(
    allowed_tools={"get_weather", "get_forecast"},
    allowed_resources={"weather://*"},
    max_requests_per_minute=100
)

test_client = ClientConfig(
    client_id="test-client",
    client_secret="test-secret",
    policy=test_policy
)
```

### Adding New MCP Servers

1. Update the `MCPServerManager.load_server_config()` method
2. Add server configuration with command, args, and environment
3. Implement actual MCP communication in `send_request()` method

## Security Considerations

### Threat Model

The gateway protects against:
- **Malicious MCP servers**: Policy enforcement prevents unauthorized access
- **Compromised clients**: Rate limiting and validation prevent abuse
- **Data exfiltration**: Response sanitization removes sensitive data
- **DoS attacks**: Rate limiting and request size limits
- **Injection attacks**: Input validation and sanitization

### Best Practices

1. **Use strong authentication tokens**
2. **Implement least-privilege policies**
3. **Monitor audit logs regularly**
4. **Keep dependencies updated**
5. **Use HTTPS in production**
6. **Implement proper error handling**
7. **Regular security audits**

## License

This project is provided as an MVP example. Enhance and adapt according to your security requirements.

## Contributing

This is an MVP implementation. Key areas for contribution:
- Real MCP server communication implementation
- Enhanced security features
- Performance optimizations
- Comprehensive testing
- Documentation improvements
