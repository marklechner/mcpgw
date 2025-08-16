"""
MCP Gateway Core Components

Core intent-aware security components for Mutual Intent Agreement (MIA).
"""

from .intent_contract import (
    ClientIntentDeclaration,
    ServerCapabilityDeclaration,
    IntentContract,
    IntentCompatibilityResult,
    IntentCompatibilityStatus,
    IntentTransactionValidation,
    IntentValidationResult
)

from .intent_broker import IntentBroker

__all__ = [
    "ClientIntentDeclaration",
    "ServerCapabilityDeclaration", 
    "IntentContract",
    "IntentCompatibilityResult",
    "IntentCompatibilityStatus",
    "IntentTransactionValidation",
    "IntentValidationResult",
    "IntentBroker"
]
