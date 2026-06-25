"""crewai-trust-gate -- CrewAI tools for Trust Gate post-quantum receipts.

Two tools that any CrewAI agent can register:

  MintActionReceiptTool    -- mints a tamper-evident receipt for a consequential action.
  VerifyReceiptTool        -- verifies a Trust Gate receipt from its certificate alone.

Receipts signed Ed25519 + ML-DSA-65; PQ-required verify defaults on.

Usage:
    from crewai_trust_gate import MintActionReceiptTool, VerifyReceiptTool
    agent = Agent(role="auditor", tools=[VerifyReceiptTool()])
"""
from crewai_trust_gate.tool import MintActionReceiptTool, VerifyReceiptTool

__version__ = "0.1.0"
__all__ = ["MintActionReceiptTool", "VerifyReceiptTool", "__version__"]
