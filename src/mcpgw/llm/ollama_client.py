"""
Ollama Client for Intent Analysis

Provides LLM-powered intent analysis using local Ollama instance.
This enables semantic understanding of client intents and server capabilities
without relying on external cloud services.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import aiohttp
from dataclasses import asdict

from ..core.intent_contract import (
    ClientIntentDeclaration,
    ServerCapabilityDeclaration,
    IntentCompatibilityResult,
    IntentCompatibilityStatus,
    IntentTransactionValidation,
    IntentValidationResult
)

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for communicating with local Ollama instance"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gpt-oss20b-128k"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure session is available"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from Ollama"""
        await self._ensure_session()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2048,  # Significantly increase response length
                "temperature": 0.1,   # More deterministic for JSON
                "top_p": 0.9,
                "num_ctx": 4096,     # Increase context window
                "repeat_penalty": 1.1,
                "stop": []  # Remove stop tokens that might truncate
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with self.session.post(f"{self.base_url}/api/generate", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error {response.status}: {error_text}")
                
                result = await response.json()
                response_text = result.get("response", "")
                
                # Log the raw response for debugging
                logger.debug(f"Raw Ollama response length: {len(response_text)}")
                logger.debug(f"Raw Ollama response: {response_text[:500]}...")
                
                return response_text
        
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise Exception(f"Ollama connection failed: {e}")
    
    async def health_check(self) -> bool:
        """Check if Ollama is available and model is loaded"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    tags = await response.json()
                    models = [model["name"] for model in tags.get("models", [])]
                    return self.model in models
                return False
        except:
            return False

class OllamaIntentAnalyzer:
    """LLM-powered intent analysis using Ollama"""
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with robust error handling and cleanup"""
        try:
            # First try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Clean up the response
        cleaned_response = response.strip()
        
        # Remove markdown code blocks
        import re
        if cleaned_response.startswith('```'):
            # Extract content between code blocks
            code_block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if code_block_match:
                cleaned_response = code_block_match.group(1).strip()
        
        # Remove JavaScript-style comments
        cleaned_response = re.sub(r'//.*?(?=\n|$)', '', cleaned_response, flags=re.MULTILINE)
        cleaned_response = re.sub(r'/\*.*?\*/', '', cleaned_response, flags=re.DOTALL)
        
        # Try parsing the cleaned response
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON object patterns
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested objects
            r'\{.*?\}',  # Basic object pattern
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, cleaned_response, re.DOTALL)
            for match in matches:
                try:
                    # Clean up common issues
                    cleaned = match.strip()
                    
                    # Remove comments again in case they're inside the JSON
                    cleaned = re.sub(r'//.*?(?=\n|$)', '', cleaned, flags=re.MULTILINE)
                    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
                    
                    # Fix common JSON issues
                    cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas
                    cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove trailing commas in arrays
                    cleaned = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', cleaned)  # Quote unquoted keys
                    
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
        
        # If all else fails, return a fallback structure
        logger.warning(f"Could not parse JSON response, using fallback. Response: {response[:200]}...")
        return {
            "status": "analysis_failed",
            "confidence_score": 0.0,
            "compatibility_reasons": ["Failed to parse LLM response"],
            "suggested_constraints": [],
            "risk_assessment": {"error": "JSON parsing failed"},
            "validation_result": "invalid",
            "validation_reasons": ["Failed to parse LLM response"],
            "intent_alignment_score": 0.0,
            "risk_factors": ["parsing_error"],
            "suggested_action": "deny"
        }
    
    async def analyze_intent_compatibility(
        self,
        client_intent: ClientIntentDeclaration,
        server_capability: ServerCapabilityDeclaration
    ) -> IntentCompatibilityResult:
        """
        Analyze compatibility between client intent and server capability using sophisticated LLM analysis.
        
        This is the core of the MIA system - semantic understanding of intent alignment.
        """
        
        system_prompt = """You are an AI security analyst specializing in Mutual Intent Agreement (MIA) systems. Your role is to perform deep semantic analysis of client intentions and server capabilities to determine compatibility for secure AI tool interactions.

CORE PRINCIPLES:
1. Semantic Understanding: Analyze the MEANING and PURPOSE behind requests, not just keywords
2. Intent Alignment: Evaluate if the client's declared purpose genuinely aligns with server capabilities
3. Risk Assessment: Identify potential security, privacy, and misuse risks
4. Constraint Synthesis: Recommend specific constraints to ensure safe interaction

ANALYSIS FRAMEWORK:
- Purpose Alignment: Does the client's stated purpose match what the server provides?
- Scope Compatibility: Are the client's data requirements within server boundaries?
- Constraint Consistency: Do client constraints align with server limitations?
- Risk Factors: What are the potential security and privacy implications?
- Trust Indicators: Are there signs of legitimate vs. potentially malicious intent?

RESPONSE FORMAT: Provide detailed JSON analysis with reasoning."""

        prompt = f"""Perform comprehensive intent compatibility analysis:

CLIENT INTENT DECLARATION:
Purpose: "{client_intent.purpose}"
Data Requirements: {client_intent.data_requirements}
Constraints: {client_intent.constraints}
Duration: {client_intent.duration} minutes
Context: {client_intent.context}

SERVER CAPABILITY DECLARATION:
Provides: {server_capability.provides}
Boundaries: {server_capability.boundaries}
Supported Operations: {server_capability.supported_operations}
Data Sensitivity: {server_capability.data_sensitivity}
Rate Limits: {server_capability.rate_limits}

ANALYSIS REQUIRED:
1. Semantic Purpose Analysis: Does the client's purpose genuinely align with server capabilities?
2. Data Requirement Assessment: Are client data needs compatible with server boundaries?
3. Constraint Evaluation: Do client and server constraints create a secure interaction space?
4. Risk Assessment: What are the security, privacy, and misuse risks?
5. Trust Evaluation: Are there indicators of legitimate vs. potentially malicious intent?

Provide analysis as JSON:
{{
  "status": "compatible|incompatible|requires_negotiation|analysis_failed",
  "confidence_score": 0.0-1.0,
  "compatibility_reasons": ["detailed reasoning for compatibility decision"],
  "incompatibility_reasons": ["specific issues if incompatible"],
  "suggested_constraints": ["additional constraints to ensure safety"],
  "risk_assessment": {{
    "risk_level": "low|medium|high|critical",
    "risk_factors": [
      {{
        "factor": "specific risk category",
        "severity": "low|medium|high",
        "description": "detailed risk description",
        "mitigation": "suggested mitigation strategy"
      }}
    ],
    "trust_indicators": ["positive indicators of legitimate intent"],
    "concern_indicators": ["potential red flags or concerns"]
  }},
  "semantic_analysis": {{
    "purpose_clarity": 0.0-1.0,
    "scope_alignment": 0.0-1.0,
    "constraint_consistency": 0.0-1.0,
    "data_sensitivity_match": 0.0-1.0
  }},
  "recommended_contract_terms": {{
    "agreed_purpose": "refined purpose statement",
    "operational_boundaries": ["specific operational limits"],
    "monitoring_requirements": ["what should be monitored"],
    "violation_triggers": ["what constitutes a violation"]
  }}
}}"""

        try:
            logger.info(f"🧠 Performing semantic intent compatibility analysis...")
            logger.info(f"Client Purpose: {client_intent.purpose}")
            logger.info(f"Server Provides: {server_capability.provides}")
            
            response = await self.ollama.generate(prompt, system_prompt)
            
            # Parse JSON response with robust error handling
            analysis = self._parse_json_response(response)
            
            # Validate and create result
            status_str = analysis.get("status", "analysis_failed")
            try:
                status = IntentCompatibilityStatus(status_str)
            except ValueError:
                logger.warning(f"Invalid status '{status_str}', defaulting to analysis_failed")
                status = IntentCompatibilityStatus.ANALYSIS_FAILED
            
            # Extract semantic analysis scores
            semantic_analysis = analysis.get("semantic_analysis", {})
            risk_assessment = analysis.get("risk_assessment", {})
            
            logger.info(f"🎯 Compatibility Analysis Complete:")
            logger.info(f"  Status: {status.value}")
            logger.info(f"  Confidence: {analysis.get('confidence_score', 0.0):.2f}")
            logger.info(f"  Risk Level: {risk_assessment.get('risk_level', 'unknown')}")
            
            return IntentCompatibilityResult(
                status=status,
                confidence_score=float(analysis.get("confidence_score", 0.0)),
                compatibility_reasons=analysis.get("compatibility_reasons", []),
                suggested_constraints=analysis.get("suggested_constraints", []),
                risk_assessment=risk_assessment,
                analysis_metadata={
                    "model": self.ollama.model,
                    "analysis_time": "utcnow",
                    "semantic_scores": semantic_analysis,
                    "recommended_terms": analysis.get("recommended_contract_terms", {}),
                    "raw_response_length": len(response)
                }
            )
        
        except Exception as e:
            logger.error(f"Intent compatibility analysis failed: {e}")
            return IntentCompatibilityResult(
                status=IntentCompatibilityStatus.ANALYSIS_FAILED,
                confidence_score=0.0,
                compatibility_reasons=[f"Analysis failed: {str(e)}"],
                suggested_constraints=[],
                risk_assessment={"error": str(e), "risk_level": "unknown"},
                analysis_metadata={"error": str(e)}
            )
    
    async def validate_transaction_intent(
        self,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]],
        contract_purpose: str,
        contract_constraints: List[str]
    ) -> IntentTransactionValidation:
        """Validate a specific transaction against the agreed intent contract"""
        
        system_prompt = """You are an AI security analyst validating MCP transactions against agreed intent contracts.

Your job is to determine if a specific request/response aligns with the agreed purpose and respects the constraints.

Focus on:
1. Intent alignment - Does this transaction serve the agreed purpose?
2. Constraint compliance - Are all constraints being respected?
3. Anomaly detection - Is this transaction suspicious or unusual?
4. Risk factors - What security risks does this transaction present?

Respond with a JSON object containing:
- validation_result: "valid", "invalid", "suspicious", or "drift_detected"
- confidence_score: float between 0.0 and 1.0
- validation_reasons: array of strings explaining the decision
- intent_alignment_score: float between 0.0 and 1.0
- risk_factors: array of identified risk factors
- suggested_action: "allow", "deny", "flag", or "require_review"
"""

        prompt = f"""
Validate this transaction against the agreed intent contract:

AGREED PURPOSE: {contract_purpose}
CONSTRAINTS: {contract_constraints}

REQUEST:
{json.dumps(request_data, indent=2)}

RESPONSE:
{json.dumps(response_data, indent=2) if response_data else "No response yet"}

Provide your validation analysis as a JSON object:
"""

        try:
            response = await self.ollama.generate(prompt, system_prompt)
            
            # Parse JSON response with robust error handling
            analysis = self._parse_json_response(response)
            
            # Validate and create result
            result_str = analysis.get("validation_result", "invalid")
            try:
                validation_result = IntentValidationResult(result_str)
            except ValueError:
                validation_result = IntentValidationResult.INVALID
            
            return IntentTransactionValidation(
                contract_id="",  # Will be set by caller
                transaction_id="",  # Will be set by caller
                validation_result=validation_result,
                confidence_score=float(analysis.get("confidence_score", 0.0)),
                validation_reasons=analysis.get("validation_reasons", []),
                intent_alignment_score=float(analysis.get("intent_alignment_score", 0.0)),
                risk_factors=analysis.get("risk_factors", []),
                suggested_action=analysis.get("suggested_action", "deny")
            )
        
        except Exception as e:
            logger.error(f"Transaction intent validation failed: {e}")
            return IntentTransactionValidation(
                contract_id="",
                transaction_id="",
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=[f"Validation failed: {str(e)}"],
                intent_alignment_score=0.0,
                risk_factors=["analysis_failure"],
                suggested_action="deny"
            )
    
    async def validate_server_response(
        self,
        client_intent: 'ClientIntentDeclaration',
        server_capability: 'ServerCapabilityDeclaration', 
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        contract_constraints: List[str]
    ) -> 'ServerResponseValidation':
        """
        Validate server response to protect client from malicious servers
        
        This analyzes whether the server response:
        - Contains only data the client requested
        - Respects client's privacy constraints
        - Doesn't include tracking or unexpected data
        - Complies with the agreed contract terms
        """
        from ..core.intent_contract import ServerResponseValidation, IntentValidationResult
        
        system_prompt = """You are an AI security analyst specializing in protecting clients from malicious MCP servers. Your role is to analyze server responses to ensure they comply with the client's declared intent and constraints.

CORE PRINCIPLES:
1. Client Protection: Ensure servers don't violate client privacy or constraints
2. Data Scope Validation: Verify response contains only requested data types
3. Privacy Enforcement: Detect attempts to include tracking or personal data
4. Contract Compliance: Ensure response aligns with agreed terms

ANALYSIS FRAMEWORK:
- Data Compliance: Does response contain only what client requested?
- Privacy Violations: Any personal/tracking data when client said "no_personal_data"?
- Unexpected Data: Fields or data types not in client's requirements?
- Constraint Violations: Any violations of client's declared constraints?

Respond with a JSON object containing:
{
    "validation_result": "valid|invalid|suspicious",
    "confidence_score": 0.0-1.0,
    "validation_reasons": ["reason1", "reason2"],
    "data_compliance_score": 0.0-1.0,
    "privacy_violations": ["violation1", "violation2"],
    "data_leakage_risks": ["risk1", "risk2"],
    "unexpected_data": ["field1", "field2"],
    "suggested_action": "allow|sanitize|deny|flag"
}"""

        user_prompt = f"""Analyze this server response for client protection:

CLIENT INTENT:
Purpose: {client_intent.purpose}
Data Requirements: {client_intent.data_requirements}
Constraints: {client_intent.constraints}

SERVER CAPABILITY:
Provides: {server_capability.provides}
Boundaries: {server_capability.boundaries}

CONTRACT CONSTRAINTS:
{contract_constraints}

ORIGINAL REQUEST:
{json.dumps(request_data, indent=2)}

SERVER RESPONSE:
{json.dumps(response_data, indent=2)}

ANALYSIS QUESTIONS:
1. Does the response contain only data types the client requested?
2. Are there any privacy violations given client constraints?
3. Is there unexpected data not in client's requirements?
4. Does the response respect all contract constraints?
5. Are there signs of tracking or data collection attempts?

Provide detailed analysis focusing on protecting the client from potential server malice."""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=user_prompt,
                system=system_prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 2048
                }
            )
            
            # Parse JSON response
            response_text = response.get('response', '').strip()
            
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback parsing
                analysis = self._extract_json_from_text(response_text)
            
            # Create validation result
            validation_result_map = {
                "valid": IntentValidationResult.VALID,
                "invalid": IntentValidationResult.INVALID,
                "suspicious": IntentValidationResult.SUSPICIOUS
            }
            
            return ServerResponseValidation(
                contract_id="",  # Will be set by caller
                transaction_id="",  # Will be set by caller
                validation_result=validation_result_map.get(
                    analysis.get("validation_result", "invalid"),
                    IntentValidationResult.INVALID
                ),
                confidence_score=float(analysis.get("confidence_score", 0.0)),
                validation_reasons=analysis.get("validation_reasons", []),
                data_compliance_score=float(analysis.get("data_compliance_score", 0.0)),
                privacy_violations=analysis.get("privacy_violations", []),
                data_leakage_risks=analysis.get("data_leakage_risks", []),
                unexpected_data=analysis.get("unexpected_data", []),
                suggested_action=analysis.get("suggested_action", "deny")
            )
            
        except Exception as e:
            logger.error(f"Server response validation failed: {e}")
            return ServerResponseValidation(
                contract_id="",
                transaction_id="",
                validation_result=IntentValidationResult.INVALID,
                confidence_score=0.0,
                validation_reasons=[f"Analysis failed: {str(e)}"],
                data_compliance_score=0.0,
                privacy_violations=["analysis_error"],
                data_leakage_risks=["validation_failed"],
                unexpected_data=[],
                suggested_action="deny"
            )

    async def analyze_intent_drift(
        self,
        original_purpose: str,
        recent_transactions: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze if client behavior is drifting from original intent"""
        
        system_prompt = """You are an AI security analyst detecting intent drift in MCP interactions.

Your job is to analyze recent transactions and determine if the client's behavior is drifting from their originally declared intent.

Focus on:
1. Pattern changes - Are the types of requests changing?
2. Scope creep - Is the client accessing data outside their original scope?
3. Behavioral anomalies - Are there unusual patterns in the requests?
4. Intent evolution - Is the client's actual intent different from declared?

Respond with a JSON object containing:
- drift_detected: boolean
- drift_severity: "low", "medium", "high"
- drift_indicators: array of specific indicators
- recommended_action: "continue", "review", "renegotiate", "terminate"
- confidence_score: float between 0.0 and 1.0
"""

        prompt = f"""
Analyze potential intent drift:

ORIGINAL PURPOSE: {original_purpose}
TIME WINDOW: Last {time_window_hours} hours

RECENT TRANSACTIONS:
{json.dumps(recent_transactions, indent=2)}

Provide your drift analysis as a JSON object:
"""

        try:
            response = await self.ollama.generate(prompt, system_prompt)
            
            # Parse JSON response with robust error handling
            analysis = self._parse_json_response(response)
            
            return analysis
        
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
