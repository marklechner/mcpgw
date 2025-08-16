"""
Weather MCP Server Example

A simple MCP server that provides weather data for demonstration of
Mutual Intent Agreement (MIA) flow. This server declares its capabilities
and boundaries clearly for intent-based security.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random

logger = logging.getLogger(__name__)

class WeatherMCPServer:
    """
    Example MCP server providing weather data with clear capability boundaries.
    
    This server demonstrates how MCP servers should declare their capabilities
    and boundaries for intent-based security analysis.
    """
    
    def __init__(self):
        self.server_info = {
            "name": "weather-server",
            "version": "1.0.0",
            "description": "Provides public weather data for travel and planning purposes"
        }
        
        # Server capability declaration
        self.capabilities = {
            "provides": [
                "current_weather",
                "weather_forecast", 
                "location_weather",
                "travel_weather_advice"
            ],
            "boundaries": [
                "public_data_only",
                "no_personal_info_storage",
                "no_location_tracking",
                "rate_limited_access",
                "travel_focused_responses"
            ],
            "rate_limits": {
                "requests_per_minute": 60,
                "data_points_per_hour": 1000,
                "forecast_days_max": 14
            },
            "data_sensitivity": "public",
            "supported_operations": ["read", "query", "aggregate"],
            "data_sources": ["public_weather_apis", "meteorological_services"],
            "retention_policy": "no_data_retention",
            "geographic_scope": "global"
        }
        
        # Mock weather data for demonstration
        self.mock_weather_data = {
            "paris": {
                "current": {
                    "temperature": 18,
                    "condition": "partly_cloudy",
                    "humidity": 65,
                    "wind_speed": 12,
                    "uv_index": 4
                },
                "forecast": [
                    {"day": 1, "high": 22, "low": 15, "condition": "sunny", "rain_chance": 10},
                    {"day": 2, "high": 20, "low": 14, "condition": "cloudy", "rain_chance": 30},
                    {"day": 3, "high": 19, "low": 13, "condition": "light_rain", "rain_chance": 70},
                    {"day": 4, "high": 23, "low": 16, "condition": "sunny", "rain_chance": 5},
                    {"day": 5, "high": 25, "low": 18, "condition": "sunny", "rain_chance": 0}
                ]
            },
            "london": {
                "current": {
                    "temperature": 15,
                    "condition": "overcast",
                    "humidity": 78,
                    "wind_speed": 18,
                    "uv_index": 2
                },
                "forecast": [
                    {"day": 1, "high": 17, "low": 12, "condition": "light_rain", "rain_chance": 60},
                    {"day": 2, "high": 16, "low": 11, "condition": "overcast", "rain_chance": 40},
                    {"day": 3, "high": 19, "low": 13, "condition": "partly_cloudy", "rain_chance": 20},
                    {"day": 4, "high": 21, "low": 15, "condition": "sunny", "rain_chance": 10},
                    {"day": 5, "high": 18, "low": 14, "condition": "cloudy", "rain_chance": 35}
                ]
            },
            "tokyo": {
                "current": {
                    "temperature": 26,
                    "condition": "sunny",
                    "humidity": 55,
                    "wind_speed": 8,
                    "uv_index": 7
                },
                "forecast": [
                    {"day": 1, "high": 28, "low": 22, "condition": "sunny", "rain_chance": 5},
                    {"day": 2, "high": 29, "low": 23, "condition": "partly_cloudy", "rain_chance": 15},
                    {"day": 3, "high": 27, "low": 21, "condition": "thunderstorms", "rain_chance": 85},
                    {"day": 4, "high": 24, "low": 19, "condition": "light_rain", "rain_chance": 65},
                    {"day": 5, "high": 26, "low": 20, "condition": "partly_cloudy", "rain_chance": 25}
                ]
            }
        }
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """Return server capability declaration for MIA negotiation"""
        return {
            "server_info": self.server_info,
            "capabilities": self.capabilities,
            "tools": self.get_available_tools(),
            "resources": self.get_available_resources()
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools"""
        return [
            {
                "name": "get_current_weather",
                "description": "Get current weather conditions for a specific location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or location"
                        }
                    },
                    "required": ["location"]
                },
                "intent_alignment": ["travel_planning", "weather_checking", "location_research"]
            },
            {
                "name": "get_weather_forecast",
                "description": "Get weather forecast for a location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or location"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of forecast days (1-14)",
                            "minimum": 1,
                            "maximum": 14,
                            "default": 5
                        }
                    },
                    "required": ["location"]
                },
                "intent_alignment": ["travel_planning", "event_planning", "weather_analysis"]
            },
            {
                "name": "get_travel_weather_advice",
                "description": "Get weather-based travel advice for a location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Destination city or location"
                        },
                        "travel_dates": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Travel dates in YYYY-MM-DD format"
                        },
                        "activity_type": {
                            "type": "string",
                            "enum": ["outdoor", "indoor", "mixed", "business"],
                            "description": "Type of travel activities planned"
                        }
                    },
                    "required": ["location"]
                },
                "intent_alignment": ["travel_planning", "vacation_planning", "business_travel"]
            }
        ]
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Return list of available resources"""
        return [
            {
                "uri": "weather://current/{location}",
                "name": "Current Weather Data",
                "description": "Real-time weather conditions for any location",
                "mimeType": "application/json"
            },
            {
                "uri": "weather://forecast/{location}",
                "name": "Weather Forecast Data", 
                "description": "Multi-day weather forecast for any location",
                "mimeType": "application/json"
            },
            {
                "uri": "weather://travel-advice/{location}",
                "name": "Travel Weather Advice",
                "description": "Weather-based travel recommendations",
                "mimeType": "application/json"
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution with intent awareness"""
        
        if tool_name == "get_current_weather":
            return await self._get_current_weather(arguments.get("location", ""))
        
        elif tool_name == "get_weather_forecast":
            return await self._get_weather_forecast(
                arguments.get("location", ""),
                arguments.get("days", 5)
            )
        
        elif tool_name == "get_travel_weather_advice":
            return await self._get_travel_weather_advice(
                arguments.get("location", ""),
                arguments.get("travel_dates", []),
                arguments.get("activity_type", "mixed")
            )
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _get_current_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for location"""
        location_key = location.lower()
        
        if location_key in self.mock_weather_data:
            weather = self.mock_weather_data[location_key]["current"]
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Current weather in {location.title()}:\n"
                               f"Temperature: {weather['temperature']}°C\n"
                               f"Condition: {weather['condition'].replace('_', ' ').title()}\n"
                               f"Humidity: {weather['humidity']}%\n"
                               f"Wind: {weather['wind_speed']} km/h\n"
                               f"UV Index: {weather['uv_index']}\n\n"
                               f"This data is provided for travel planning and general information purposes."
                    }
                ],
                "metadata": {
                    "location": location,
                    "data_source": "public_weather_service",
                    "timestamp": datetime.utcnow().isoformat(),
                    "intent_context": "weather_information"
                }
            }
        else:
            # Generate mock data for unknown locations
            temp = random.randint(10, 30)
            conditions = ["sunny", "partly_cloudy", "cloudy", "light_rain"]
            condition = random.choice(conditions)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Current weather in {location.title()}:\n"
                               f"Temperature: {temp}°C\n"
                               f"Condition: {condition.replace('_', ' ').title()}\n"
                               f"Humidity: {random.randint(40, 80)}%\n"
                               f"Wind: {random.randint(5, 25)} km/h\n"
                               f"UV Index: {random.randint(1, 10)}\n\n"
                               f"This is simulated data for demonstration purposes."
                    }
                ],
                "metadata": {
                    "location": location,
                    "data_source": "simulated_data",
                    "timestamp": datetime.utcnow().isoformat(),
                    "intent_context": "weather_information"
                }
            }
    
    async def _get_weather_forecast(self, location: str, days: int) -> Dict[str, Any]:
        """Get weather forecast for location"""
        location_key = location.lower()
        days = min(max(days, 1), 14)  # Enforce boundaries
        
        if location_key in self.mock_weather_data:
            forecast = self.mock_weather_data[location_key]["forecast"][:days]
            
            forecast_text = f"{days}-day weather forecast for {location.title()}:\n\n"
            
            for day_data in forecast:
                forecast_text += (
                    f"Day {day_data['day']}: "
                    f"{day_data['high']}°C/{day_data['low']}°C, "
                    f"{day_data['condition'].replace('_', ' ').title()}, "
                    f"{day_data['rain_chance']}% chance of rain\n"
                )
            
            forecast_text += "\nThis forecast is ideal for travel planning and outdoor activity scheduling."
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": forecast_text
                    }
                ],
                "metadata": {
                    "location": location,
                    "forecast_days": days,
                    "data_source": "public_weather_service",
                    "timestamp": datetime.utcnow().isoformat(),
                    "intent_context": "travel_planning"
                }
            }
        else:
            # Generate mock forecast
            forecast_text = f"{days}-day weather forecast for {location.title()}:\n\n"
            
            for day in range(1, days + 1):
                high = random.randint(15, 30)
                low = high - random.randint(5, 10)
                conditions = ["sunny", "partly_cloudy", "cloudy", "light_rain"]
                condition = random.choice(conditions)
                rain_chance = random.randint(0, 80)
                
                forecast_text += (
                    f"Day {day}: {high}°C/{low}°C, "
                    f"{condition.replace('_', ' ').title()}, "
                    f"{rain_chance}% chance of rain\n"
                )
            
            forecast_text += "\nThis is simulated forecast data for demonstration purposes."
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": forecast_text
                    }
                ],
                "metadata": {
                    "location": location,
                    "forecast_days": days,
                    "data_source": "simulated_data",
                    "timestamp": datetime.utcnow().isoformat(),
                    "intent_context": "travel_planning"
                }
            }
    
    async def _get_travel_weather_advice(
        self, 
        location: str, 
        travel_dates: List[str], 
        activity_type: str
    ) -> Dict[str, Any]:
        """Get travel weather advice for location and dates"""
        
        # Get forecast data
        forecast_data = await self._get_weather_forecast(location, 7)
        
        # Generate travel advice based on activity type
        advice_text = f"Travel weather advice for {location.title()}:\n\n"
        
        if activity_type == "outdoor":
            advice_text += (
                "🌤️ OUTDOOR ACTIVITIES FOCUS:\n"
                "- Best days for outdoor activities: Days with sunny/partly cloudy conditions\n"
                "- Pack sunscreen for high UV days\n"
                "- Bring rain gear for days with >50% rain chance\n"
                "- Consider indoor alternatives for rainy days\n\n"
            )
        elif activity_type == "business":
            advice_text += (
                "💼 BUSINESS TRAVEL FOCUS:\n"
                "- Weather should not significantly impact indoor meetings\n"
                "- Pack appropriate clothing for temperature range\n"
                "- Allow extra travel time on rainy days\n"
                "- Consider weather for any outdoor business events\n\n"
            )
        else:
            advice_text += (
                "🎒 GENERAL TRAVEL ADVICE:\n"
                "- Pack layers for temperature variations\n"
                "- Include rain protection for wet weather days\n"
                "- Plan indoor activities for poor weather days\n"
                "- Take advantage of sunny days for sightseeing\n\n"
            )
        
        advice_text += (
            "PACKING RECOMMENDATIONS:\n"
            "- Light jacket for cooler temperatures\n"
            "- Umbrella or rain jacket\n"
            "- Comfortable walking shoes\n"
            "- Weather-appropriate clothing\n\n"
            "This advice is based on current weather forecasts and may change. "
            "Check updated forecasts closer to your travel dates."
        )
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": advice_text
                }
            ],
            "metadata": {
                "location": location,
                "activity_type": activity_type,
                "travel_dates": travel_dates,
                "advice_type": "weather_based_travel_planning",
                "timestamp": datetime.utcnow().isoformat(),
                "intent_context": "travel_planning"
            }
        }
    
    async def handle_resource_request(self, uri: str) -> Dict[str, Any]:
        """Handle resource requests"""
        
        if uri.startswith("weather://current/"):
            location = uri.split("/")[-1]
            return await self._get_current_weather(location)
        
        elif uri.startswith("weather://forecast/"):
            location = uri.split("/")[-1]
            return await self._get_weather_forecast(location, 5)
        
        elif uri.startswith("weather://travel-advice/"):
            location = uri.split("/")[-1]
            return await self._get_travel_weather_advice(location, [], "mixed")
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")

# Example usage and testing
async def main():
    """Test the weather server"""
    server = WeatherMCPServer()
    
    print("Weather MCP Server Capabilities:")
    print(json.dumps(server.get_server_capabilities(), indent=2))
    
    print("\n" + "="*50)
    print("Testing Tools:")
    
    # Test current weather
    result = await server.handle_tool_call("get_current_weather", {"location": "Paris"})
    print("\nCurrent Weather (Paris):")
    print(result["content"][0]["text"])
    
    # Test forecast
    result = await server.handle_tool_call("get_weather_forecast", {"location": "London", "days": 3})
    print("\nWeather Forecast (London, 3 days):")
    print(result["content"][0]["text"])
    
    # Test travel advice
    result = await server.handle_tool_call("get_travel_weather_advice", {
        "location": "Tokyo",
        "travel_dates": ["2024-03-15", "2024-03-16", "2024-03-17"],
        "activity_type": "outdoor"
    })
    print("\nTravel Weather Advice (Tokyo, Outdoor):")
    print(result["content"][0]["text"])

if __name__ == "__main__":
    asyncio.run(main())
