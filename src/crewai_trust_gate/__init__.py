"""crewai-trust-gate -- CrewAI tools for Trust Gate signed receipts.

Five tools that any CrewAI agent can register:

  MintActionReceiptTool    -- mints a tamper-evident receipt for a consequential action.
  VerifyReceiptTool        -- verifies a Trust Gate receipt; pass expected_kid to pin the signer.
  GateDecisionTool         -- two-phase PREVIEW -> COMMIT gate; PREVIEW returns a verdict
                               (ALLOW, DENY, ESCALATE), COMMIT signs a receipt and returns
                               a permit (GRANTED only for ALLOW).
  CheckEgressTool          -- flags data NO_MARKERS_FOUND/INTERNAL/CONFIDENTIAL/RESTRICTED
                               before it leaves; it cannot block.
  RunExitDrillTool         -- vendor exit-readiness drill. Informational; it signs a receipt.

Receipts are signed with Ed25519, plus ML-DSA-65 when the server has a post-quantum backend. PQ-required verify defaults on at the server, which
rejects a receipt with no verified post-quantum signature. Pin the signer with expected_kid.

Usage:
    from crewai_trust_gate import MintActionReceiptTool, VerifyReceiptTool
    agent = Agent(role="auditor", tools=[VerifyReceiptTool()])
"""
from crewai_trust_gate.tool import (
    CheckEgressTool,
    GateDecisionTool,
    MintActionReceiptTool,
    RunExitDrillTool,
    VerifyReceiptTool,
)

__version__ = "0.3.0"
__all__ = [
    "MintActionReceiptTool",
    "VerifyReceiptTool",
    "GateDecisionTool",
    "CheckEgressTool",
    "RunExitDrillTool",
    "__version__",
]
