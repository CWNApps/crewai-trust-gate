"""CrewAI `BaseTool` wrappers around the hosted Trust Gate MCP server.

Same transport layer as langchain-trust-gate -- one JSON-RPC POST to /mcp + one
fire-and-forget telemetry ping to /x?via=crewai. No PII, no cookies.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
except ImportError as e:
    raise ImportError(
        "crewai-trust-gate requires the crewai package. "
        "Install with: pip install crewai (or `pip install crewai-trust-gate[crewai]`)."
    ) from e


TRUST_GATE_URL = os.environ.get("TRUST_GATE_URL", "https://trust-gate-mcp.onrender.com")
_VIA = "crewai"


def _mcp_call(method: str, arguments: Dict[str, Any], *, timeout: float = 30.0) -> Dict[str, Any]:
    """One JSON-RPC tools/call against the hosted Trust Gate MCP server."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            f"{TRUST_GATE_URL}/mcp",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-03-26",
            },
        )
        r.raise_for_status()
        body = r.json()
    if "error" in body:
        raise RuntimeError(f"Trust Gate MCP error: {body['error']}")
    result = body.get("result", {})
    if isinstance(result, dict):
        if "structuredContent" in result:
            return result["structuredContent"]
        if "content" in result and result["content"]:
            try:
                import json
                return json.loads(result["content"][0]["text"])
            except (KeyError, ValueError, IndexError):
                return {"raw": result["content"]}
    return result if isinstance(result, dict) else {"raw": result}


def _ping_telemetry(kind: str = "api") -> None:
    """Fire-and-forget channel-attribution ping."""
    try:
        with httpx.Client(timeout=2.0) as client:
            client.get(f"{TRUST_GATE_URL}/x", params={"via": _VIA, "kind": kind})
    except Exception:  # noqa: BLE001 -- telemetry is best-effort; ANY failure must be swallowed
        pass


# --- mint_action_receipt --------------------------------------------------------------
class MintActionReceiptInput(BaseModel):
    agent_id: str = Field(description="Identifier of the agent performing the action.")
    operation: str = Field(description="Operation name (e.g., 'deploy', 'send_email').")
    target: str = Field(description="Target of the action.")
    policy: Optional[str] = Field(default="agent action evidence")
    inputs: Optional[str] = Field(default=None)
    decision: Optional[str] = Field(default="ACTION_GOVERNED")


class MintActionReceiptTool(BaseTool):
    name: str = "trust_gate_mint_action_receipt"
    description: str = (
        "Mint a post-quantum, tamper-evident receipt for a consequential agent action. "
        "Returns a receipt that's verifiable offline from the certificate alone. "
        "Receipt is signed Ed25519 + ML-DSA-65; carries a 128-bit kid for offline "
        "same-notary check."
    )
    args_schema: Type[BaseModel] = MintActionReceiptInput

    def _run(self, agent_id: str, operation: str, target: str,
             policy: Optional[str] = None, inputs: Optional[str] = None,
             decision: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        _ping_telemetry()
        args = {
            "agent_id": agent_id,
            "operation": operation,
            "target": target,
            "policy": policy or "agent action evidence",
        }
        if inputs is not None:
            args["inputs"] = inputs
        if decision is not None:
            args["decision"] = decision
        return _mcp_call("mint_action_receipt", args)


# --- verify_receipt -------------------------------------------------------------------
class VerifyReceiptInput(BaseModel):
    receipt: Dict[str, Any] = Field(description="The Trust Gate receipt to verify.")
    require_pq: Optional[bool] = Field(
        default=None,
        description="None=obey TRUST_GATE_REQUIRE_PQ (default true). False=Ed25519-only OK.")


class VerifyReceiptTool(BaseTool):
    name: str = "trust_gate_verify_receipt"
    description: str = (
        "Verify a Trust Gate receipt from the certificate alone (offline). "
        "Returns {ok, hash_ok, sig_ok, signed, legs, signature_alg, reason}. "
        "Defaults to PQ-required mode -- defends against Ed25519-only downgrade by "
        "requiring at least one verified PQ leg."
    )
    args_schema: Type[BaseModel] = VerifyReceiptInput

    def _run(self, receipt: Dict[str, Any],
             require_pq: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
        _ping_telemetry()
        args: Dict[str, Any] = {"receipt": receipt}
        if require_pq is not None:
            args["require_pq"] = require_pq
        return _mcp_call("verify_receipt", args)
