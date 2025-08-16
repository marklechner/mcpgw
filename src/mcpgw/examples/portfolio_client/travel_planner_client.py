"""
Travel Planner Client Example

Demonstrates a client that uses the MIA Gateway to access weather data
for travel planning purposes. Shows the complete Mutual Intent Agreement flow.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)

class TravelPlannerClient:
    """
    Example client that demonstrates intent-based MCP interaction.
    
    This client declares its intent to use weather data for travel planning,
    negotiates an intent contract, and then makes validated requests.
    """
    
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Client identity and intent
        self.client_info = {
            "name": "travel-planner-client",
            "version": "1.0.0",
            "description": "AI-powered travel planning assistant"
        }
        
        # Intent declaration for travel planning
        self.intent_declaration = {
            "purpose": "I need weather data to help users plan their travel itineraries and provide weather-based travel recommendations",
            "data_requirements": [
                "current_weather_conditions",
                "weather_forecasts",
                "location_based_weather",
                "travel_weather_advice"
            ],
            "constraints": [
                "read_only_access",
                "no_personal_data_storage",
                "travel_planning_context_only",
                "public_weather_data_only",
                "no_location_tracking"
            ],
            "duration": 120,  # 2 hours session
            "context": {
                "use_case": "travel_planning_assistant",
                "user_facing": True,
                "data_retention": "none",
                "geographic_scope": "global",
                "typical_queries": [
                    "weather for destination cities",
                    "multi-day forecasts for trip planning",
                    "weather-based activity recommendations"
                ]
            }
        }
        
        # Session state
        self.intent_id: Optional[str] = None
        self.contract_id: Optional[str] = None
        self.is_authenticated: bool = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def initialize_mia_session(self) -> Dict[str, Any]:
        """
        Initialize MIA session by declaring intent and negotiating contract.
        
        This demonstrates the complete 3-phase MIA process:
        1. Declare client intent
        2. Negotiate with server capability 
        3. Establish validated session
        """
        await self._ensure_session()
        
        logger.info("Starting MIA session initialization...")
        
        # Phase 1: Declare Intent
        logger.info("Phase 1: Declaring client intent...")
        intent_response = await self._declare_intent()
        
        if not intent_response.get("intent_id"):
            raise Exception("Failed to declare intent")
        
        self.intent_id = intent_response["intent_id"]
        logger.info(f"Intent declared successfully: {self.intent_id}")
        
        # Phase 2: Find compatible server capability
        logger.info("Phase 2: Finding compatible server capability...")
        
        # In a real implementation, this would discover available servers
        # For demo, we'll use the pre-registered weather server capability
        server_capability_id = await self._find_weather_server_capability()
        
        if not server_capability_id:
            raise Exception("No compatible server capability found")
        
        # Phase 2: Negotiate Contract
        logger.info("Phase 2: Negotiating intent contract...")
        contract_response = await self._negotiate_contract(server_capability_id)
        
        if not contract_response.get("contract_id") or contract_response.get("status") != "active":
            raise Exception(f"Contract negotiation failed: {contract_response}")
        
        self.contract_id = contract_response["contract_id"]
        self.is_authenticated = True
        
        logger.info(f"MIA session established successfully!")
        logger.info(f"Contract ID: {self.contract_id}")
        logger.info(f"Agreed Purpose: {contract_response['agreed_purpose']}")
        
        return {
            "status": "success",
            "intent_id": self.intent_id,
            "contract_id": self.contract_id,
            "session_info": contract_response
        }
    
    async def _declare_intent(self) -> Dict[str, Any]:
        """Phase 1: Declare client intent to the gateway"""
        
        async with self.session.post(
            f"{self.gateway_url}/intent/declare",
            json=self.intent_declaration
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Intent declaration failed: {response.status} - {error_text}")
            
            return await response.json()
    
    async def _find_weather_server_capability(self) -> Optional[str]:
        """Find weather server capability ID by querying available capabilities"""
        
        try:
            # Query available server capabilities from the gateway
            async with self.session.get(f"{self.gateway_url}/intent/capabilities") as response:
                if response.status == 200:
                    capabilities_data = await response.json()
                    capabilities = capabilities_data.get("capabilities", [])
                    
                    # Look for weather-related capability
                    for capability in capabilities:
                        provides = capability.get("provides", [])
                        # Check if this capability provides weather-related services
                        if any(service in ["weather_data", "forecasts", "weather", "climate_info"] 
                               for service in provides):
                            logger.info(f"Found weather server capability: {capability['capability_id']}")
                            return capability["capability_id"]
                    
                    logger.warning("No weather server capability found in available capabilities")
                    return None
                else:
                    logger.error(f"Failed to query capabilities: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error finding weather server capability: {e}")
            return None
    
    async def _negotiate_contract(self, server_capability_id: str) -> Dict[str, Any]:
        """Phase 2: Negotiate intent contract"""
        
        negotiation_request = {
            "client_intent_id": self.intent_id,
            "server_capability_id": server_capability_id,
            "additional_constraints": [
                "demo_mode_enabled",
                "educational_purposes"
            ]
        }
        
        async with self.session.post(
            f"{self.gateway_url}/intent/negotiate",
            json=negotiation_request
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Contract negotiation failed: {response.status} - {error_text}")
            
            return await response.json()
    
    async def get_weather_for_destination(self, destination: str) -> Dict[str, Any]:
        """Get current weather for a travel destination"""
        
        if not self.is_authenticated or not self.contract_id:
            raise Exception("MIA session not initialized. Call initialize_mia_session() first.")
        
        mcp_request = {
            "contract_id": self.contract_id,
            "server_name": "weather-server",
            "request": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_current_weather",
                    "arguments": {
                        "location": destination
                    }
                },
                "id": f"weather-{datetime.now(timezone.utc).timestamp()}"
            }
        }
        
        async with self.session.post(
            f"{self.gateway_url}/mcp/request",
            json=mcp_request
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Weather request failed: {response.status} - {error_text}")
            
            return await response.json()
    
    async def get_travel_forecast(self, destination: str, days: int = 5) -> Dict[str, Any]:
        """Get weather forecast for travel planning"""
        
        if not self.is_authenticated or not self.contract_id:
            raise Exception("MIA session not initialized. Call initialize_mia_session() first.")
        
        mcp_request = {
            "contract_id": self.contract_id,
            "server_name": "weather-server",
            "request": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_weather_forecast",
                    "arguments": {
                        "location": destination,
                        "days": days
                    }
                },
                "id": f"forecast-{datetime.now(timezone.utc).timestamp()}"
            }
        }
        
        async with self.session.post(
            f"{self.gateway_url}/mcp/request",
            json=mcp_request
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Forecast request failed: {response.status} - {error_text}")
            
            return await response.json()
    
    async def get_travel_weather_advice(
        self, 
        destination: str, 
        travel_dates: List[str], 
        activity_type: str = "mixed"
    ) -> Dict[str, Any]:
        """Get weather-based travel advice"""
        
        if not self.is_authenticated or not self.contract_id:
            raise Exception("MIA session not initialized. Call initialize_mia_session() first.")
        
        mcp_request = {
            "contract_id": self.contract_id,
            "server_name": "weather-server",
            "request": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_travel_weather_advice",
                    "arguments": {
                        "location": destination,
                        "travel_dates": travel_dates,
                        "activity_type": activity_type
                    }
                },
                "id": f"advice-{datetime.now(timezone.utc).timestamp()}"
            }
        }
        
        async with self.session.post(
            f"{self.gateway_url}/mcp/request",
            json=mcp_request
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Travel advice request failed: {response.status} - {error_text}")
            
            return await response.json()
    
    async def plan_trip(self, destinations: List[str], activity_type: str = "mixed") -> Dict[str, Any]:
        """
        Complete travel planning workflow demonstrating multiple MIA-validated requests
        """
        
        if not self.is_authenticated:
            raise Exception("MIA session not initialized")
        
        trip_plan = {
            "destinations": destinations,
            "activity_type": activity_type,
                "planning_date": datetime.now(timezone.utc).isoformat(),
            "weather_data": {},
            "recommendations": []
        }
        
        logger.info(f"Planning trip for destinations: {destinations}")
        
        # Get weather data for each destination
        for destination in destinations:
            logger.info(f"Getting weather data for {destination}...")
            
            try:
                # Get current weather
                current_weather = await self.get_weather_for_destination(destination)
                
                # Get forecast
                forecast = await self.get_travel_forecast(destination, 7)
                
                # Get travel advice
                travel_dates = [
                    (datetime.now(timezone.utc) + timedelta(days=i)).strftime("%Y-%m-%d")
                    for i in range(1, 8)
                ]
                advice = await self.get_travel_weather_advice(destination, travel_dates, activity_type)
                
                trip_plan["weather_data"][destination] = {
                    "current_weather": current_weather,
                    "forecast": forecast,
                    "travel_advice": advice
                }
                
                # Generate recommendation based on weather
                if current_weather.get("result"):
                    # Handle different response formats
                    weather_text = ""
                    result = current_weather["result"]
                    
                    if isinstance(result, dict):
                        if "content" in result and isinstance(result["content"], list) and len(result["content"]) > 0:
                            weather_text = result["content"][0].get("text", "")
                        elif "text" in result:
                            weather_text = result["text"]
                        elif "data" in result:
                            weather_text = str(result["data"])
                        else:
                            weather_text = str(result)
                    elif isinstance(result, str):
                        weather_text = result
                    else:
                        weather_text = str(result)
                    
                    if weather_text:
                        if "sunny" in weather_text.lower() or "partly cloudy" in weather_text.lower():
                            recommendation = f"✅ {destination}: Great weather conditions for travel!"
                        elif "rain" in weather_text.lower():
                            recommendation = f"🌧️ {destination}: Pack rain gear - wet weather expected"
                        else:
                            recommendation = f"🌤️ {destination}: Check weather closer to travel date"
                        
                        trip_plan["recommendations"].append(recommendation)
                
                logger.info(f"Weather data collected for {destination}")
                
            except Exception as e:
                logger.error(f"Failed to get weather data for {destination}: {e}")
                trip_plan["weather_data"][destination] = {"error": str(e)}
        
        return trip_plan
    
    async def get_session_status(self) -> Dict[str, Any]:
        """Get current MIA session status"""
        
        if not self.contract_id:
            return {"status": "no_session", "authenticated": False}
        
        async with self.session.get(
            f"{self.gateway_url}/intent/contracts/{self.contract_id}"
        ) as response:
            if response.status == 200:
                contract_stats = await response.json()
                return {
                    "status": "active",
                    "authenticated": self.is_authenticated,
                    "contract_id": self.contract_id,
                    "intent_id": self.intent_id,
                    "contract_stats": contract_stats
                }
            else:
                return {"status": "error", "authenticated": False}

# Demo scenarios
async def demo_travel_planning_scenario():
    """Demonstrate complete travel planning scenario with MIA"""
    
    print("🌍 Travel Planner Client - MIA Demonstration")
    print("=" * 60)
    
    async with TravelPlannerClient() as client:
        try:
            # Initialize MIA session
            print("\n🔐 Initializing MIA Session...")
            session_info = await client.initialize_mia_session()
            print(f"✅ MIA Session established!")
            print(f"   Contract ID: {session_info['contract_id']}")
            print(f"   Intent: {session_info['session_info']['agreed_purpose']}")
            
            # Plan a multi-destination trip
            print("\n🗺️ Planning Multi-Destination Trip...")
            destinations = ["Paris", "London", "Tokyo"]
            trip_plan = await client.plan_trip(destinations, "outdoor")
            
            print(f"✅ Trip planned for {len(destinations)} destinations")
            
            # Display recommendations
            print("\n📋 Travel Recommendations:")
            for recommendation in trip_plan["recommendations"]:
                print(f"   {recommendation}")
            
            # Show detailed weather for one destination
            print(f"\n🌤️ Detailed Weather for Paris:")
            if "Paris" in trip_plan["weather_data"]:
                paris_weather = trip_plan["weather_data"]["Paris"]["current_weather"]
                if paris_weather.get("result"):
                    # Handle different response formats safely
                    result = paris_weather["result"]
                    weather_text = ""
                    
                    if isinstance(result, dict):
                        if "content" in result and isinstance(result["content"], list) and len(result["content"]) > 0:
                            weather_text = result["content"][0].get("text", "")
                        elif "text" in result:
                            weather_text = result["text"]
                        elif "data" in result:
                            weather_text = str(result["data"])
                        else:
                            weather_text = str(result)
                    elif isinstance(result, str):
                        weather_text = result
                    else:
                        weather_text = str(result)
                    
                    if weather_text:
                        print(f"   {weather_text}")
                    else:
                        print(f"   Weather data available but format not recognized")
                else:
                    print(f"   No weather result available")
            else:
                print(f"   No weather data available for Paris")
            
            # Get session statistics
            print("\n📊 Session Statistics:")
            session_status = await client.get_session_status()
            if session_status.get("contract_stats"):
                stats = session_status["contract_stats"]
                print(f"   Transactions: {stats.get('transaction_count', 0)}")
                print(f"   Success Rate: {stats.get('success_rate', 0):.2%}")
                print(f"   Violations: {stats.get('violation_count', 0)}")
            
            print("\n✅ MIA Demonstration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            logger.error(f"Demo scenario failed: {e}")

async def demo_intent_violation_scenario():
    """Demonstrate what happens when client violates intent"""
    
    print("\n🚨 Intent Violation Demonstration")
    print("=" * 50)
    
    async with TravelPlannerClient() as client:
        try:
            # Initialize session
            await client.initialize_mia_session()
            print("✅ MIA Session established")
            
            # Try to make a request that violates the travel planning intent
            print("\n🚫 Attempting request that violates intent...")
            
            # This would be a request for non-travel related weather data
            # or attempting to access personal/private data
            violation_request = {
                "contract_id": client.contract_id,
                "server_name": "weather-server",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_personal_location_history",  # This violates intent
                        "arguments": {
                            "user_id": "12345"
                        }
                    },
                    "id": "violation-test"
                }
            }
            
            async with client.session.post(
                f"{client.gateway_url}/mcp/request",
                json=violation_request
            ) as response:
                result = await response.json()
                
                if result.get("error"):
                    print("✅ Intent violation correctly detected and blocked!")
                    print(f"   Error: {result['error']['message']}")
                    if result['error'].get('data'):
                        print(f"   Validation Result: {result['error']['data'].get('validation_result')}")
                        print(f"   Reasons: {result['error']['data'].get('reasons')}")
                else:
                    print("❌ Intent violation was not detected!")
            
        except Exception as e:
            print(f"❌ Violation demo failed: {e}")

async def main():
    """Run all demo scenarios"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Travel Planner Client Demonstrations")
    
    # Run main travel planning demo
    await demo_travel_planning_scenario()
    
    # Run intent violation demo
    await demo_intent_violation_scenario()
    
    print("\n🎉 All demonstrations completed!")

if __name__ == "__main__":
    asyncio.run(main())
