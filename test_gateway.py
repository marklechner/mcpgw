#!/usr/bin/env python3
"""
Test script for MCP Gateway

This script demonstrates how to interact with the MCP Gateway,
including client registration and making MCP requests.
"""

import requests
import json
import time
from typing import Dict, Any

class MCPGatewayClient:
    """Simple client for testing the MCP Gateway"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check gateway health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def register_client(self, client_id: str, client_secret: str, policy: Dict[str, Any]) -> str:
        """Register a new client and get token"""
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "policy": policy
        }
        
        response = self.session.post(
            f"{self.base_url}/admin/register-client",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        self.token = result["token"]
        return self.token
    
    def set_token(self, token: str):
        """Set authentication token"""
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def list_servers(self) -> Dict[str, Any]:
        """List available MCP servers"""
        if not self.token:
            raise ValueError("No authentication token set")
        
        response = self.session.get(f"{self.base_url}/servers")
        response.raise_for_status()
        return response.json()
    
    def send_mcp_request(self, server_name: str, method: str, params: Dict[str, Any] = None, request_id: str = "1") -> Dict[str, Any]:
        """Send MCP request through gateway"""
        if not self.token:
            raise ValueError("No authentication token set")
        
        payload = {
            "server_name": server_name,
            "request": {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": request_id
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/mcp/request",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_audit_logs(self) -> Dict[str, Any]:
        """Get audit logs"""
        if not self.token:
            raise ValueError("No authentication token set")
        
        response = self.session.get(f"{self.base_url}/audit/logs")
        response.raise_for_status()
        return response.json()

def test_gateway():
    """Test the MCP Gateway functionality"""
    print("🚀 Testing MCP Gateway")
    print("=" * 50)
    
    client = MCPGatewayClient()
    
    # Test 1: Health check
    print("\n1. Health Check")
    try:
        health = client.health_check()
        print(f"✅ Gateway is healthy: {health['status']}")
        print(f"   Version: {health['version']}")
        print(f"   Timestamp: {health['timestamp']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test 2: Register client
    print("\n2. Client Registration")
    try:
        policy = {
            "allowed_tools": ["get_weather", "get_forecast"],
            "allowed_resources": ["weather://*"],
            "max_requests_per_minute": 100,
            "require_auth": True,
            "sandbox_mode": True
        }
        
        token = client.register_client("test-client-demo", "demo-secret", policy)
        print(f"✅ Client registered successfully")
        print(f"   Token: {token[:20]}...")
        
        # Set token for subsequent requests
        client.set_token(token)
        
    except Exception as e:
        print(f"❌ Client registration failed: {e}")
        return
    
    # Test 3: List servers
    print("\n3. List MCP Servers")
    try:
        servers = client.list_servers()
        print(f"✅ Available servers: {servers['servers']}")
        print(f"   Client ID: {servers['client_id']}")
    except Exception as e:
        print(f"❌ Failed to list servers: {e}")
        return
    
    # Test 4: Send MCP requests
    print("\n4. MCP Requests")
    
    # Test 4a: List tools
    try:
        response = client.send_mcp_request("example-weather", "tools/list")
        print("✅ Tools list request successful")
        print(f"   Available tools: {len(response.get('result', {}).get('tools', []))}")
        if response.get('result', {}).get('tools'):
            for tool in response['result']['tools']:
                print(f"   - {tool['name']}: {tool['description']}")
    except Exception as e:
        print(f"❌ Tools list request failed: {e}")
    
    # Test 4b: Call tool
    try:
        params = {
            "name": "get_weather",
            "arguments": {"city": "San Francisco"}
        }
        response = client.send_mcp_request("example-weather", "tools/call", params)
        print("✅ Tool call request successful")
        if response.get('result', {}).get('content'):
            content = response['result']['content'][0]['text']
            print(f"   Response: {content}")
    except Exception as e:
        print(f"❌ Tool call request failed: {e}")
    
    # Test 5: Rate limiting test
    print("\n5. Rate Limiting Test")
    try:
        print("   Sending multiple requests quickly...")
        success_count = 0
        rate_limited_count = 0
        
        for i in range(5):
            try:
                response = client.send_mcp_request("example-weather", "tools/list")
                success_count += 1
                print(f"   Request {i+1}: ✅")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    rate_limited_count += 1
                    print(f"   Request {i+1}: ⚠️ Rate limited")
                else:
                    print(f"   Request {i+1}: ❌ Error {e.response.status_code}")
            time.sleep(0.1)  # Small delay
        
        print(f"   Successful: {success_count}, Rate limited: {rate_limited_count}")
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
    
    # Test 6: Policy violation test
    print("\n6. Policy Violation Test")
    try:
        # Try to call a tool not in allowed list
        params = {
            "name": "unauthorized_tool",
            "arguments": {"param": "value"}
        }
        response = client.send_mcp_request("example-weather", "tools/call", params)
        print("⚠️ Policy violation test: Request should have been blocked")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("✅ Policy violation correctly blocked")
        else:
            print(f"❌ Unexpected error: {e.response.status_code}")
    except Exception as e:
        print(f"❌ Policy violation test failed: {e}")
    
    # Test 7: Audit logs
    print("\n7. Audit Logs")
    try:
        logs = client.get_audit_logs()
        print(f"✅ Retrieved audit logs: {logs['total_entries']} total entries")
        print(f"   Recent entries: {len(logs['logs'])}")
        
        if logs['logs']:
            recent_log = logs['logs'][-1]
            print(f"   Latest: {recent_log['method']} -> {recent_log['success']}")
            
    except Exception as e:
        print(f"❌ Failed to get audit logs: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Gateway testing completed!")

def test_unauthorized_access():
    """Test unauthorized access scenarios"""
    print("\n🔒 Testing Unauthorized Access")
    print("=" * 50)
    
    client = MCPGatewayClient()
    
    # Test without token
    print("\n1. Request without authentication")
    try:
        servers = client.list_servers()
        print("❌ Request should have been rejected")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("✅ Unauthorized request correctly rejected")
        else:
            print(f"❌ Unexpected status code: {e.response.status_code}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test with invalid token
    print("\n2. Request with invalid token")
    try:
        client.set_token("invalid-token-12345")
        servers = client.list_servers()
        print("❌ Request should have been rejected")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("✅ Invalid token correctly rejected")
        else:
            print(f"❌ Unexpected status code: {e.response.status_code}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    print("MCP Gateway Test Suite")
    print("Make sure the gateway is running on http://localhost:8000")
    print()
    
    try:
        # Test main functionality
        test_gateway()
        
        # Test security
        test_unauthorized_access()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
