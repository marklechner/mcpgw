"""
Intent Contract Data Models

Defines the core data structures for Mutual Intent Agreement (MIA) system.
These models represent the binding agreements between clients and servers
based on declared intents rather than static permissions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import uuid

class IntentCompatibilityStatus(Enum):
    """Status of intent compatibility analysis"""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REQUIRES_NEGOTIATION = "requires_negotiation"
    ANALYSIS_FAILED = "analysis_failed"

class IntentValidationResult(Enum):
    """Result of intent validation for a transaction"""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    DRIFT_DETECTED = "drift_detected"

@dataclass
class ClientIntentDeclaration:
    """Client's declaration of their intent for MCP server interaction"""
    purpose: str                           # "Analyze portfolio risk for investment decisions"
    data_requirements: List[str]           # ["market_data", "price_history", "volatility_metrics"]
    constraints: List[str]                 # ["no_trading", "read_only", "no_pii"]
    duration: Optional[int] = None         # Session duration in minutes
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    declared_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "purpose": self.purpose,
            "data_requirements": self.data_requirements,
            "constraints": self.constraints,
            "duration": self.duration,
            "context": self.context,
            "client_id": self.client_id,
            "declared_at": self.declared_at.isoformat()
        }

@dataclass
class ServerCapabilityDeclaration:
    """Server's declaration of its capabilities and boundaries"""
    provides: List[str]                    # ["market_data", "analytics", "forecasting"]
    boundaries: List[str]                  # ["no_pii", "aggregated_only", "public_data_only"]
    rate_limits: Dict[str, int]           # {"requests_per_minute": 100, "data_points_per_hour": 10000}
    data_sensitivity: str                  # "public", "restricted", "confidential"
    supported_operations: List[str]        # ["read", "analyze", "aggregate"]
    server_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    registered_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "provides": self.provides,
            "boundaries": self.boundaries,
            "rate_limits": self.rate_limits,
            "data_sensitivity": self.data_sensitivity,
            "supported_operations": self.supported_operations,
            "server_id": self.server_id,
            "registered_at": self.registered_at.isoformat()
        }

@dataclass
class IntentCompatibilityResult:
    """Result of intent compatibility analysis"""
    status: IntentCompatibilityStatus
    confidence_score: float               # 0.0 to 1.0
    compatibility_reasons: List[str]      # Reasons for compatibility/incompatibility
    suggested_constraints: List[str]      # Additional constraints if needed
    risk_assessment: Dict[str, Any]       # Risk factors identified
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "compatibility_reasons": self.compatibility_reasons,
            "suggested_constraints": self.suggested_constraints,
            "risk_assessment": self.risk_assessment,
            "analysis_metadata": self.analysis_metadata
        }

@dataclass
class IntentContract:
    """Binding agreement between client and server based on intent analysis"""
    contract_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_intent: ClientIntentDeclaration = None
    server_capability: ServerCapabilityDeclaration = None
    compatibility_result: IntentCompatibilityResult = None
    
    # Contract terms derived from negotiation
    agreed_purpose: str = ""
    allowed_operations: List[str] = field(default_factory=list)
    data_access_scope: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    
    # Contract lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    violation_count: int = 0
    last_validated: Optional[datetime] = None
    
    # Monitoring
    transaction_count: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    
    def __post_init__(self):
        """Set expiration based on client intent duration"""
        if self.client_intent and self.client_intent.duration:
            self.expires_at = self.created_at + timedelta(minutes=self.client_intent.duration)
    
    def is_expired(self) -> bool:
        """Check if contract has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def record_transaction(self, success: bool):
        """Record a transaction against this contract"""
        self.transaction_count += 1
        if success:
            self.successful_transactions += 1
        else:
            self.failed_transactions += 1
        self.last_validated = datetime.utcnow()
    
    def record_violation(self):
        """Record an intent violation"""
        self.violation_count += 1
        # Deactivate contract if too many violations
        if self.violation_count >= 5:
            self.is_active = False
    
    def get_success_rate(self) -> float:
        """Get transaction success rate"""
        if self.transaction_count == 0:
            return 0.0
        return self.successful_transactions / self.transaction_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "contract_id": self.contract_id,
            "client_intent": self.client_intent.to_dict() if self.client_intent else None,
            "server_capability": self.server_capability.to_dict() if self.server_capability else None,
            "compatibility_result": self.compatibility_result.to_dict() if self.compatibility_result else None,
            "agreed_purpose": self.agreed_purpose,
            "allowed_operations": self.allowed_operations,
            "data_access_scope": self.data_access_scope,
            "constraints": self.constraints,
            "rate_limits": self.rate_limits,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "violation_count": self.violation_count,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "transaction_count": self.transaction_count,
            "successful_transactions": self.successful_transactions,
            "failed_transactions": self.failed_transactions
        }

@dataclass
class ServerResponseValidation:
    """Result of validating server response against client's declared intent"""
    contract_id: str
    transaction_id: str
    validation_result: IntentValidationResult
    confidence_score: float
    validation_reasons: List[str]
    data_compliance_score: float          # How well response complies with client constraints
    privacy_violations: List[str]         # Detected privacy violations
    data_leakage_risks: List[str]         # Potential data leakage risks
    unexpected_data: List[str]            # Data not requested by client
    suggested_action: str                 # "allow", "sanitize", "deny", "flag"
    validated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "contract_id": self.contract_id,
            "transaction_id": self.transaction_id,
            "validation_result": self.validation_result.value,
            "confidence_score": self.confidence_score,
            "validation_reasons": self.validation_reasons,
            "data_compliance_score": self.data_compliance_score,
            "privacy_violations": self.privacy_violations,
            "data_leakage_risks": self.data_leakage_risks,
            "unexpected_data": self.unexpected_data,
            "suggested_action": self.suggested_action,
            "validated_at": self.validated_at.isoformat()
        }

@dataclass
class IntentTransactionValidation:
    """Result of validating a specific transaction against an intent contract"""
    contract_id: str
    transaction_id: str
    validation_result: IntentValidationResult
    confidence_score: float
    validation_reasons: List[str]
    intent_alignment_score: float         # How well transaction aligns with declared intent
    risk_factors: List[str]               # Identified risk factors
    suggested_action: str                 # "allow", "deny", "flag", "require_review"
    validated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Bidirectional protection
    client_protection: Optional['ServerResponseValidation'] = None
    server_protection: bool = True        # Whether server is protected from this request
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "contract_id": self.contract_id,
            "transaction_id": self.transaction_id,
            "validation_result": self.validation_result.value,
            "confidence_score": self.confidence_score,
            "validation_reasons": self.validation_reasons,
            "intent_alignment_score": self.intent_alignment_score,
            "risk_factors": self.risk_factors,
            "suggested_action": self.suggested_action,
            "validated_at": self.validated_at.isoformat(),
            "client_protection": self.client_protection.to_dict() if self.client_protection else None,
            "server_protection": self.server_protection
        }

@dataclass
class ClientProtectionPolicy:
    """Policy defining how to protect clients from malicious servers"""
    client_id: str
    allowed_data_types: Set[str]          # Types of data client expects to receive
    forbidden_data_types: Set[str]        # Types of data client must not receive
    max_response_size: Optional[int] = None  # Maximum response size in bytes
    require_data_provenance: bool = False    # Require data source information
    sanitize_responses: bool = True          # Apply response sanitization
    detect_tracking_attempts: bool = True    # Detect server tracking attempts
    block_unexpected_fields: bool = True     # Block fields not in client's data requirements
    privacy_level: str = "standard"          # "minimal", "standard", "strict"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "client_id": self.client_id,
            "allowed_data_types": list(self.allowed_data_types),
            "forbidden_data_types": list(self.forbidden_data_types),
            "max_response_size": self.max_response_size,
            "require_data_provenance": self.require_data_provenance,
            "sanitize_responses": self.sanitize_responses,
            "detect_tracking_attempts": self.detect_tracking_attempts,
            "block_unexpected_fields": self.block_unexpected_fields,
            "privacy_level": self.privacy_level
        }
