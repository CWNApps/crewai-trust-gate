"""Tests for crewai-trust-gate. Same shape as the langchain suite -- mocked transport,
checks JSON-RPC envelope + telemetry + PQ-required passthrough + tool metadata."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

import crewai_trust_gate.tool as tool_mod
from crewai_trust_gate import MintActionReceiptTool, VerifyReceiptTool


def _mcp_response(structured: dict):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={
        "jsonrpc": "2.0", "id": 1,
        "result": {"structuredContent": structured},
    })
    return resp


def test_mcp_call_envelope():
    captured = {}
    def fake_post(self, url, json=None, headers=None, **kw):
        captured["url"] = url
        captured["json"] = json
        return _mcp_response({"ok": True})

    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", new=lambda *a, **kw: MagicMock()):
        tool_mod._mcp_call("mint_action_receipt", {"agent_id": "a", "operation": "o", "target": "t"})

    assert captured["json"]["method"] == "tools/call"
    assert captured["json"]["params"]["name"] == "mint_action_receipt"


def test_telemetry_via_crewai():
    pings = []
    def fake_get(self, url, params=None, **kw):
        pings.append(params)
        return MagicMock()

    with patch("httpx.Client.post", return_value=_mcp_response({"ok": True})), \
         patch("httpx.Client.get", new=fake_get):
        MintActionReceiptTool()._run(agent_id="a", operation="o", target="t")

    assert pings[0]["via"] == "crewai"
    assert pings[0]["kind"] == "api"


def test_telemetry_failure_never_breaks_tool():
    def fake_get(self, *a, **kw):
        import httpx
        raise httpx.ConnectError("network down")

    with patch("httpx.Client.post", return_value=_mcp_response({"ok": True})), \
         patch("httpx.Client.get", new=fake_get):
        out = MintActionReceiptTool()._run(agent_id="a", operation="o", target="t")
    assert out["ok"] is True


def test_verify_passes_require_pq():
    captured = {}
    def fake_post(self, url, json=None, **kw):
        captured["args"] = json["params"]["arguments"]
        return _mcp_response({"ok": True})

    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", return_value=MagicMock()):
        VerifyReceiptTool()._run(receipt={"atom_id": "x"}, require_pq=False)
    assert captured["args"]["require_pq"] is False


def test_verify_default_omits_require_pq():
    captured = {}
    def fake_post(self, url, json=None, **kw):
        captured["args"] = json["params"]["arguments"]
        return _mcp_response({"ok": True})

    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", return_value=MagicMock()):
        VerifyReceiptTool()._run(receipt={"atom_id": "x"})
    assert "require_pq" not in captured["args"]


def test_tool_metadata_is_crewai_compatible():
    t = MintActionReceiptTool()
    assert t.name == "trust_gate_mint_action_receipt"
    assert "ML-DSA-65" in t.description
    sch = t.args_schema.model_json_schema()
    for f in ("agent_id", "operation", "target"):
        assert f in sch["properties"]


def test_mcp_call_raises_on_error():
    err_resp = MagicMock()
    err_resp.raise_for_status = MagicMock()
    err_resp.json = MagicMock(return_value={"jsonrpc": "2.0", "error": {"code": -1, "message": "nope"}})
    with patch("httpx.Client.post", return_value=err_resp), patch("httpx.Client.get", return_value=MagicMock()):
        with pytest.raises(RuntimeError, match="Trust Gate MCP error"):
            tool_mod._mcp_call("verify_receipt", {"receipt": {}})


# ---- 0.3.0: pinning the signer, and no claim the server's 0.3.0 documentation withdrew ------------
def test_verify_passes_expected_kid_through():
    captured = {}
    def fake_post(self, url, json=None, **kw):
        captured["args"] = json["params"]["arguments"]
        return _mcp_response({"ok": True, "signer_pinned": True})
    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", return_value=MagicMock()):
        VerifyReceiptTool()._run(receipt={"atom_id": "x"}, expected_kid="0123456789abcdef0123456789abcdef")
    assert captured["args"]["expected_kid"] == "0123456789abcdef0123456789abcdef"


def test_verify_default_omits_expected_kid():
    captured = {}
    def fake_post(self, url, json=None, **kw):
        captured["args"] = json["params"]["arguments"]
        return _mcp_response({"ok": True})
    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", return_value=MagicMock()):
        VerifyReceiptTool()._run(receipt={"atom_id": "x"})
    assert "expected_kid" not in captured["args"]


WITHDRAWN = ("certificate alone", "same notary", "same-notary", "execution permit", "Blocks RESTRICTED",
             "blocks RESTRICTED", "no side effects", "No side effects", "SLH-DSA", "defeats", "defends against",
             "data export", "who signed")


def _all_descriptions():
    from crewai_trust_gate import (CheckEgressTool, GateDecisionTool, MintActionReceiptTool,
                                 RunExitDrillTool, VerifyReceiptTool)
    return {c.__name__: c().description for c in (MintActionReceiptTool, VerifyReceiptTool, GateDecisionTool,
                                                  CheckEgressTool, RunExitDrillTool)}


def test_no_description_makes_a_claim_the_server_withdrew():
    for name, text in _all_descriptions().items():
        for phrase in WITHDRAWN:
            assert phrase.lower() not in text.lower(), (name, phrase)


def test_descriptions_state_what_the_server_does_and_does_not_do():
    d = _all_descriptions()
    assert "expected_kid" in d["VerifyReceiptTool"]
    assert "ALLOW" in d["GateDecisionTool"] and "0.3.0" in d["GateDecisionTool"]
    assert "does not observe or block" in d["GateDecisionTool"]
    assert "cannot block" in d["CheckEgressTool"] and "NO_MARKERS_FOUND" in d["CheckEgressTool"]
    assert "signs a receipt" in d["RunExitDrillTool"] and "local signing key" in d["RunExitDrillTool"]
    assert "not contacted" in d["RunExitDrillTool"]


def test_version_is_030_everywhere():
    import pathlib, re
    import crewai_trust_gate as pkg
    toml = (pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert pkg.__version__ == "0.3.0"
    assert re.search(r'^version = "0.3.0"', toml, re.M)


# ---- an older server must not make a requested pin look like a pass ------------------------------
KID = "0123456789abcdef0123456789abcdef"


def _verify_with_response(structured, **kw):
    with patch("httpx.Client.post", return_value=_mcp_response(structured)), patch("httpx.Client.get", return_value=MagicMock()):
        return VerifyReceiptTool()._run(receipt={"atom_id": "x"}, expected_kid=KID)


def test_a_server_that_ignores_expected_kid_makes_the_tool_raise():
    for structured in ({"ok": True, "reason": "verified"}, {"result": {"ok": True, "reason": "verified"}}):
        with pytest.raises(RuntimeError, match="expected_kid"):
            _verify_with_response(structured)


def test_a_server_that_reports_the_pin_passes_through_unchanged():
    for structured in ({"ok": True, "signer_pinned": True}, {"result": {"ok": True, "signer_pinned": False}}):
        assert _verify_with_response(structured) == structured


def test_a_refusal_keeps_its_reason_instead_of_being_replaced_by_the_pin_error():
    refusal = {"ok": False, "reason": "signer mismatch"}
    assert _verify_with_response(refusal) == refusal
    assert _verify_with_response({"error": "expected_kid must be 32 hex characters"}) == {"error": "expected_kid must be 32 hex characters"}


def test_without_expected_kid_no_pin_report_is_required():
    structured = {"ok": True, "reason": "verified"}
    with patch("httpx.Client.post", return_value=_mcp_response(structured)), patch("httpx.Client.get", return_value=MagicMock()):
        assert VerifyReceiptTool()._run(receipt={"atom_id": "x"}) == structured


def test_gate_decision_sends_the_required_context():
    captured = {}
    def fake_post(self, url, json=None, **kw):
        captured["args"] = json["params"]["arguments"]
        return _mcp_response({"verdict": "ALLOW"})
    from crewai_trust_gate import GateDecisionTool
    with patch("httpx.Client.post", new=fake_post), patch("httpx.Client.get", return_value=MagicMock()):
        GateDecisionTool()._run(action="read_file", resource="docs/readme.md", context={"k": 1})
    assert captured["args"]["context"] == {"k": 1}
    assert captured["args"]["action"] == "read_file" and captured["args"]["resource"] == "docs/readme.md"
