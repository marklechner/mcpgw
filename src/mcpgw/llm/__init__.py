"""
MCP Gateway LLM Integration

Local LLM integration for intent analysis using Ollama.
"""

from .ollama_client import OllamaClient, OllamaIntentAnalyzer

__all__ = [
    "OllamaClient",
    "OllamaIntentAnalyzer"
]
