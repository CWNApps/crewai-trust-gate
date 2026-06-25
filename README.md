# crewai-trust-gate

CrewAI tools for **Trust Gate** post-quantum, tamper-evident receipts on consequential agent actions.

Trust Gate receipts are signed Ed25519 + ML-DSA-65 (FIPS 204) by the hosted MCP server (no local signing key). Each receipt is verifiable offline from the certificate alone. The hosted server defaults to PQ-required verify mode; set TRUST_GATE_REQUIRE_PQ=false to allow Ed25519-only receipts.

## Install

```bash
pip install crewai-trust-gate
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
| `trust_gate_mint_action_receipt` | Mint a post-quantum receipt for any consequential agent action. |
| `trust_gate_verify_receipt` | Verify a Trust Gate receipt from the certificate alone. |

## Configuration

```bash
export TRUST_GATE_URL="https://trust-gate-mcp.onrender.com"  # default; override for self-hosted
```

## Telemetry

One fire-and-forget `GET /x?via=crewai&kind=api` per tool call. No PII, no cookies, never blocks the tool.

## Related

* **langchain-trust-gate** -- same tools, LangChain shape
* **llama-index-trust-gate** -- same tools, LlamaIndex shape
* **Trust Gate MCP** -- the hosted server: <https://trust-gate-mcp.onrender.com>
* **Smithery** -- <https://smithery.ai/servers/apps/cwn-trust-gate>

## License

Apache-2.0.
