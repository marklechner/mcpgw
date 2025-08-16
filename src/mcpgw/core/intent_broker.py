"""
Intent Broker

Core component that orchestrates Mutual Intent Agreement (MIA) between clients and servers.
Handles intent declaration, compatibility analysis, contract negotiation, and lifecycle management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import uuid

from .intent_contract import (
    ClientIntentDeclaration,
    ServerCapabilityDeclaration,
    IntentContract,
    IntentCompatibilityResult,
    IntentCompatibilityStatus,
    IntentTransactionValidation,
    IntentValidationResult,
    ServerResponseValidation,
    ClientProtectionPolicy
)
from ..llm.ollama_client import OllamaClient, OllamaIntentAnalyzer

logger = logging.getLogger(__name__)

class IntentBroker:
    """
    Orchestrates the Mutual Intent Agreement process between clients and servers.
    
    The broker manages the three-phase MIA process:
    1. Declaration - Clients declare intent, servers register capabilities
    2. Negotiation - LLM analyzes compatibility and creates contracts
    3. Validation - Every transaction is validated against the agreed intent
    """
    
    def __init__(self, ollama_client: OllamaClient):
        self.analyzer = OllamaIntentAnalyzer(ollama_client)
        
        # Storage for active components
        self.client_intents: Dict[str, ClientIntentDeclaration] = {}
        self.server_capabilities: Dict[str, ServerCapabilityDeclaration] = {}
        self.active_contracts: Dict[str, IntentContract] = {}
        
        # Session tracking
        self.client_sessions: Dict[str, str] = {}  # client_id -> contract_id
        self.contract_transactions: Dict[str, List[Dict[str, Any]]] = {}  # contract_id -> transactions
        
        # Monitoring
        self.negotiation_stats = {
            "total_negotiations": 0,
            "successful_contracts": 0,
            "failed_negotiations": 0,
            "active_contracts": 0
        }
    
    async def declare_client_intent(self, intent: ClientIntentDeclaration) -> str:
        """
        Phase 1: Client declares their intent for MCP server interaction
        
        Returns:
            intent_id: Unique identifier for this intent declaration
        """
        intent_id = str(uuid.uuid4())
        self.client_intents[intent_id] = intent
        
        logger.info(f"Client intent declared: {intent_id} - {intent.purpose}")
        return intent_id
    
    async def register_server_capability(self, capability: ServerCapabilityDeclaration) -> str:
        """
        Phase 1: Server registers its capabilities and boundaries
        
        Returns:
            capability_id: Unique identifier for this capability declaration
        """
        capability_id = str(uuid.uuid4())
        self.server_capabilities[capability_id] = capability
        
        logger.info(f"Server capability registered: {capability_id} - {capability.provides}")
        return capability_id
    
    async def negotiate_intent_contract(
        self,
        client_intent_id: str,
        server_capability_id: str,
        additional_constraints: Optional[List[str]] = None
    ) -> IntentContract:
        """
        Phase 2: Negotiate intent contract between client and server
        
        Uses LLM to analyze compatibility and create binding agreement
        
        Args:
            client_intent_id: ID of client's intent declaration
            server_capability_id: ID of server's capability declaration
            additional_constraints: Optional additional constraints to apply
            
        Returns:
            IntentContract: The negotiated contract (may be inactive if incompatible)
        """
        self.negotiation_stats["total_negotiations"] += 1
        
        # Retrieve intent and capability
        client_intent = self.client_intents.get(client_intent_id)
        server_capability = self.server_capabilities.get(server_capability_id)
        
        if not client_intent:
            raise ValueError(f"Client intent not found: {client_intent_id}")
        if not server_capability:
            raise ValueError(f"Server capability not found: {server_capability_id}")
        
        logger.info(f"Negotiating contract between {client_intent_id} and {server_capability_id}")
        
        try:
            # Analyze compatibility using LLM
            compatibility_result = await self.analyzer.analyze_intent_compatibility(
                client_intent, server_capability
            )
            
            # Create contract based on analysis
            contract = IntentContract(
                client_intent=client_intent,
                server_capability=server_capability,
                compatibility_result=compatibility_result
            )
            
            # Determine contract terms based on compatibility analysis
            if compatibility_result.status == IntentCompatibilityStatus.COMPATIBLE:
                contract.is_active = True
                contract.agreed_purpose = client_intent.purpose
                contract.allowed_operations = server_capability.supported_operations.copy()
                contract.data_access_scope = client_intent.data_requirements.copy()
                contract.constraints = client_intent.constraints.copy()
                contract.rate_limits = server_capability.rate_limits.copy()
                
                # Apply additional constraints from analysis
                if compatibility_result.suggested_constraints:
                    contract.constraints.extend(compatibility_result.suggested_constraints)
                
                # Apply any additional constraints provided
                if additional_constraints:
                    contract.constraints.extend(additional_constraints)
                
                self.negotiation_stats["successful_contracts"] += 1
                logger.info(f"Contract successfully negotiated: {contract.contract_id}")
                
            elif compatibility_result.status == IntentCompatibilityStatus.REQUIRES_NEGOTIATION:
                # Contract created but requires manual review/approval
                contract.is_active = False
                contract.agreed_purpose = f"PENDING: {client_intent.purpose}"
                logger.warning(f"Contract requires negotiation: {contract.contract_id}")
                
            else:
                # Incompatible - create inactive contract for audit trail
                contract.is_active = False
                contract.agreed_purpose = f"REJECTED: {client_intent.purpose}"
                self.negotiation_stats["failed_negotiations"] += 1
                logger.warning(f"Contract rejected due to incompatibility: {contract.contract_id}")
            
            # Store the contract
            self.active_contracts[contract.contract_id] = contract
            
            # Initialize transaction tracking
            self.contract_transactions[contract.contract_id] = []
            
            # Update session mapping if contract is active
            if contract.is_active:
                self.client_sessions[client_intent.client_id] = contract.contract_id
                self.negotiation_stats["active_contracts"] += 1
            
            return contract
            
        except Exception as e:
            logger.error(f"Contract negotiation failed: {e}")
            self.negotiation_stats["failed_negotiations"] += 1
            
            # Create failed contract for audit trail
            failed_contract = IntentContract(
                client_intent=client_intent,
                server_capability=server_capability,
                is_active=False,
                agreed_purpose=f"FAILED: {str(e)}"
            )
            self.active_contracts[failed_contract.contract_id] = failed_contract
            
            return failed_contract
    
    async def validate_transaction(
        self,
        contract_id: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None
    ) -> IntentTransactionValidation:
        """
        Phase 3: Validate transaction against intent contract
        
        Args:
            contract_id: ID of the intent contract
            request_data: MCP request data
            response_data: MCP response data (if available)
            
        Returns:
            IntentTransactionValidation: Validation result
        """
        contract = self.active_contracts.get(contract_id)
        if not contract:
            return IntentTransactionValidation(
                contract_id=contract_id,
                transaction_id=str(uuid.uuid4()),
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=["Contract not found"],
                intent_alignment_score=0.0,
                risk_factors=["unknown_contract"],
                suggested_action="deny"
            )
        
        if not contract.is_active:
            return IntentTransactionValidation(
                contract_id=contract_id,
                transaction_id=str(uuid.uuid4()),
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=["Contract is not active"],
                intent_alignment_score=0.0,
                risk_factors=["inactive_contract"],
                suggested_action="deny"
            )
        
        if contract.is_expired():
            contract.is_active = False
            return IntentTransactionValidation(
                contract_id=contract_id,
                transaction_id=str(uuid.uuid4()),
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=["Contract has expired"],
                intent_alignment_score=0.0,
                risk_factors=["expired_contract"],
                suggested_action="deny"
            )
        
        transaction_id = str(uuid.uuid4())
        
        try:
            # Use LLM to validate transaction against contract
            validation = await self.analyzer.validate_transaction_intent(
                request_data=request_data,
                response_data=response_data,
                contract_purpose=contract.agreed_purpose,
                contract_constraints=contract.constraints
            )
            
            # Set contract and transaction IDs
            validation.contract_id = contract_id
            validation.transaction_id = transaction_id
            
            # Record transaction in contract
            success = validation.validation_result == IntentValidationResult.VALID
            contract.record_transaction(success)
            
            # Record violation if invalid
            if not success:
                contract.record_violation()
            
            # Store transaction for drift analysis
            transaction_record = {
                "transaction_id": transaction_id,
                "timestamp": datetime.utcnow().isoformat(),
                "request": request_data,
                "response": response_data,
                "validation_result": validation.validation_result.value,
                "intent_alignment_score": validation.intent_alignment_score
            }
            self.contract_transactions[contract_id].append(transaction_record)
            
            # Keep only last 100 transactions per contract
            if len(self.contract_transactions[contract_id]) > 100:
                self.contract_transactions[contract_id] = self.contract_transactions[contract_id][-100:]
            
            logger.info(f"Transaction validated: {transaction_id} - {validation.validation_result.value}")
            return validation
            
        except Exception as e:
            logger.error(f"Transaction validation failed: {e}")
            
            # Record failed transaction
            contract.record_transaction(False)
            contract.record_violation()
            
            return IntentTransactionValidation(
                contract_id=contract_id,
                transaction_id=transaction_id,
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=[f"Validation failed: {str(e)}"],
                intent_alignment_score=0.0,
                risk_factors=["validation_error"],
                suggested_action="deny"
            )
    
    async def analyze_intent_drift(self, contract_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze if client behavior is drifting from original intent
        
        Args:
            contract_id: ID of the contract to analyze
            time_window_hours: Time window for analysis
            
        Returns:
            Dict containing drift analysis results
        """
        contract = self.active_contracts.get(contract_id)
        if not contract:
            return {"error": "Contract not found"}
        
        # Get recent transactions
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_transactions = [
            tx for tx in self.contract_transactions.get(contract_id, [])
            if datetime.fromisoformat(tx["timestamp"]) > cutoff_time
        ]
        
        if not recent_transactions:
            return {
                "drift_detected": False,
                "drift_severity": "none",
                "drift_indicators": [],
                "recommended_action": "continue",
                "confidence_score": 1.0,
                "message": "No recent transactions to analyze"
            }
        
        try:
            drift_analysis = await self.analyzer.analyze_intent_drift(
                original_purpose=contract.agreed_purpose,
                recent_transactions=recent_transactions,
                time_window_hours=time_window_hours
            )
            
            # Take action based on drift analysis
            if drift_analysis.get("drift_detected", False):
                severity = drift_analysis.get("drift_severity", "unknown")
                if severity == "high":
                    contract.is_active = False
                    logger.warning(f"Contract deactivated due to high intent drift: {contract_id}")
                elif severity == "medium":
                    logger.warning(f"Medium intent drift detected for contract: {contract_id}")
            
            return drift_analysis
            
        except Exception as e:
            logger.error(f"Intent drift analysis failed: {e}")
            return {
                "drift_detected": False,
                "drift_severity": "unknown",
                "drift_indicators": [f"Analysis failed: {str(e)}"],
                "recommended_action": "review",
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    def get_contract_by_client(self, client_id: str) -> Optional[IntentContract]:
        """Get active contract for a client"""
        contract_id = self.client_sessions.get(client_id)
        if contract_id:
            return self.active_contracts.get(contract_id)
        return None
    
    def get_active_contracts(self) -> List[IntentContract]:
        """Get all active contracts"""
        return [contract for contract in self.active_contracts.values() if contract.is_active]
    
    def get_contract_stats(self, contract_id: str) -> Dict[str, Any]:
        """Get statistics for a specific contract"""
        contract = self.active_contracts.get(contract_id)
        if not contract:
            return {"error": "Contract not found"}
        
        transactions = self.contract_transactions.get(contract_id, [])
        
        return {
            "contract_id": contract_id,
            "is_active": contract.is_active,
            "created_at": contract.created_at.isoformat(),
            "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
            "transaction_count": contract.transaction_count,
            "successful_transactions": contract.successful_transactions,
            "failed_transactions": contract.failed_transactions,
            "violation_count": contract.violation_count,
            "success_rate": contract.get_success_rate(),
            "recent_transactions": len(transactions),
            "agreed_purpose": contract.agreed_purpose,
            "constraints": contract.constraints
        }
    
    def get_broker_stats(self) -> Dict[str, Any]:
        """Get overall broker statistics"""
        active_contracts = len([c for c in self.active_contracts.values() if c.is_active])
        
        return {
            **self.negotiation_stats,
            "active_contracts": active_contracts,
            "total_contracts": len(self.active_contracts),
            "client_intents": len(self.client_intents),
            "server_capabilities": len(self.server_capabilities),
            "active_sessions": len(self.client_sessions)
        }
    
    async def validate_server_response(
        self,
        contract_id: str,
        transaction_id: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> ServerResponseValidation:
        """
        Validate server response to protect client from malicious servers
        
        This provides bidirectional protection by ensuring servers don't:
        - Return data the client didn't request
        - Include tracking or privacy-violating information
        - Exceed the agreed data scope
        - Violate client's declared constraints
        
        Args:
            contract_id: ID of the intent contract
            transaction_id: ID of the transaction
            request_data: Original MCP request
            response_data: Server's MCP response
            
        Returns:
            ServerResponseValidation: Validation result for client protection
        """
        contract = self.active_contracts.get(contract_id)
        if not contract:
            return ServerResponseValidation(
                contract_id=contract_id,
                transaction_id=transaction_id,
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=["Contract not found"],
                data_compliance_score=0.0,
                privacy_violations=["unknown_contract"],
                data_leakage_risks=["contract_not_found"],
                unexpected_data=[],
                suggested_action="deny"
            )
        
        try:
            # Use LLM to analyze server response for client protection
            response_validation = await self.analyzer.validate_server_response(
                client_intent=contract.client_intent,
                server_capability=contract.server_capability,
                request_data=request_data,
                response_data=response_data,
                contract_constraints=contract.constraints
            )
            
            # Set IDs
            response_validation.contract_id = contract_id
            response_validation.transaction_id = transaction_id
            
            logger.info(f"Server response validated for client protection: {transaction_id} - {response_validation.validation_result.value}")
            return response_validation
            
        except Exception as e:
            logger.error(f"Server response validation failed: {e}")
            
            return ServerResponseValidation(
                contract_id=contract_id,
                transaction_id=transaction_id,
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=[f"Response validation failed: {str(e)}"],
                data_compliance_score=0.0,
                privacy_violations=["validation_error"],
                data_leakage_risks=["analysis_failed"],
                unexpected_data=[],
                suggested_action="deny"
            )
    
    async def validate_bidirectional_transaction(
        self,
        contract_id: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None
    ) -> IntentTransactionValidation:
        """
        Perform bidirectional validation protecting both client and server
        
        This combines:
        1. Server protection: Validate client request against intent
        2. Client protection: Validate server response against client constraints
        
        Args:
            contract_id: ID of the intent contract
            request_data: MCP request data
            response_data: MCP response data (if available)
            
        Returns:
            IntentTransactionValidation: Complete bidirectional validation result
        """
        transaction_id = str(uuid.uuid4())
        
        # First validate the request (protect server)
        request_validation = await self.validate_transaction(
            contract_id=contract_id,
            request_data=request_data,
            response_data=response_data
        )
        
        # If request is invalid, don't proceed with response validation
        if request_validation.validation_result != IntentValidationResult.VALID:
            return request_validation
        
        # If we have a response, validate it (protect client)
        if response_data:
            response_validation = await self.validate_server_response(
                contract_id=contract_id,
                transaction_id=transaction_id,
                request_data=request_data,
                response_data=response_data
            )
            
            # Attach client protection results
            request_validation.client_protection = response_validation
            
            # If response validation fails, mark overall transaction as suspicious
            if response_validation.validation_result != IntentValidationResult.VALID:
                request_validation.validation_result = IntentValidationResult.SUSPICIOUS
                request_validation.risk_factors.extend([
                    "server_response_violation",
                    "client_protection_triggered"
                ])
                request_validation.suggested_action = response_validation.suggested_action
        
        return request_validation

    async def cleanup_expired_contracts(self):
        """Clean up expired contracts and sessions"""
        expired_contracts = []
        
        for contract_id, contract in self.active_contracts.items():
            if contract.is_expired() and contract.is_active:
                contract.is_active = False
                expired_contracts.append(contract_id)
                logger.info(f"Contract expired: {contract_id}")
        
        # Remove expired sessions
        expired_sessions = []
        for client_id, contract_id in self.client_sessions.items():
            if contract_id in expired_contracts:
                expired_sessions.append(client_id)
        
        for client_id in expired_sessions:
            del self.client_sessions[client_id]
        
        # Update stats
        self.negotiation_stats["active_contracts"] = len([
            c for c in self.active_contracts.values() if c.is_active
        ])
        
        return len(expired_contracts)
