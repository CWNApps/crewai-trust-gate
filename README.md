# crewai-trust-gate

CrewAI tools for **Trust Gate**: signed receipts for agent actions, a read-only-allowlist decision gate, an egress marker check and an exit drill.

Receipts are signed Ed25519 + ML-DSA-65 by the hosted MCP server (no local signing key). A receipt's integrity can be checked offline. To know **who signed it**, verify with `expected_kid` (the kid of the server you trust): without that, anyone can generate keys and sign a receipt that verifies. The server defaults to PQ-required verify (a receipt with no verified post-quantum signature is rejected); set TRUST_GATE_REQUIRE_PQ=false on your own deployment to allow Ed25519-only receipts.

## Install

```bash
pip install cwn-crewai-trust-gate
```

## Usage

```python
from crewai import Agent, Task, Crew
from crewai_trust_gate import MintActionReceiptTool, VerifyReceiptTool

auditor = Agent(
    role="receipt auditor",
    goal="Verify every consequential action has a tamper-evident receipt",
    tools=[VerifyReceiptTool()],
)

deployer = Agent(
    role="deploy engineer",
    goal="Deploy safely, leave a receipt for every promotion",
    tools=[MintActionReceiptTool()],
)
```

## Tools

| Tool | Purpose |
|---|---|
| `trust_gate_mint_action_receipt` | Mint a signed receipt (Ed25519 + ML-DSA-65) for a consequential agent action. |
| `trust_gate_verify_receipt` | Verify a receipt offline. Pass `expected_kid` to pin the signer; the result reports `signer_pinned`. |
| `trust_gate_gate_decision` | Two-phase gate (server 0.3.0 or later). PREVIEW returns a verdict (ALLOW, DENY, ESCALATE); COMMIT signs a receipt and returns a permit, GRANTED only for ALLOW. It judges names against a read-only allowlist and does not observe or block anything. |
| `trust_gate_check_egress` | Check data for sensitivity markers (NO_MARKERS_FOUND / INTERNAL / CONFIDENTIAL / RESTRICTED) before it leaves. It flags and cannot block. |
| `trust_gate_run_exit_drill` | Vendor exit-readiness drill. Informational; it signs a receipt, which creates the signing key on first use. |

## Configuration

```bash
export TRUST_GATE_URL="https://trust-gate-mcp.onrender.com"  # default; override for self-hosted
```

## Compatibility

This release is written for Trust Gate MCP server 0.3.0 or later. Versions before 0.3.0 of the server's `gate_decision` returned GRANTED for every input: treat any GRANTED permit from a server older than 0.3.0 as not evidence. See the [security advisory](https://github.com/CWNApps/trust-gate-mcp/security/advisories/GHSA-gxfp-4vvx-wjc8).

## Telemetry

One fire-and-forget `GET /x?via=crewai&kind=api` per tool call. No PII, no cookies, never blocks the tool.

## Related

* **langchain-trust-gate** -- same tools, LangChain shape
* **llama-index-trust-gate** -- same tools, LlamaIndex shape
* **Trust Gate MCP** -- the hosted server: <https://trust-gate-mcp.onrender.com>
* **Smithery** -- <https://smithery.ai/servers/apps/cwn-trust-gate>

## License

Apache-2.0.
