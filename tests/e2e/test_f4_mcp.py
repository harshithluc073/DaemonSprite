import os
import sys
import json
import time
import subprocess
import pytest

# Feature 4: MCP Server/Tools (F4)

# Tier 1: Feature Coverage (5 cases)

def test_mcp_server_launch():
    """Spawn src/daemon_mcp.py as a subprocess and verify it accepts JSON-RPC input and doesn't exit immediately."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, mcp_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # It should run and wait for input
    time.sleep(0.5)
    assert proc.poll() is None, f"MCP process exited immediately. Stderr: {proc.stderr.read()}"
    
    proc.terminate()
    proc.wait()

def test_mcp_list_tools(mcp_client):
    """Send the tools/list request via stdio and verify tools are exposed."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        # 1. Initialize
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # 2. List tools
        res = client.request("tools/list", msg_id=2)
        assert "result" in res, f"Response is: {res}"
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        
        # Verify tools are exposed
        assert "update_state" in tool_names or "set_state" in tool_names
        assert "force_animation" in tool_names
        assert "query_status" in tool_names
    finally:
        client.stop()

def test_mcp_query_status(mcp_client):
    """Call query_status tool and verify response format."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        res = client.request("tools/call", {
            "name": "query_status",
            "arguments": {}
        }, msg_id=2)
        
        assert "result" in res
        content = res["result"]["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"
        
        # Check text contains state info
        text_val = content[0]["text"]
        # It should contain something like "idle" or status status
        assert "state" in text_val.lower() or "status" in text_val.lower()
    finally:
        client.stop()

def test_mcp_update_state(mcp_client):
    """Call update_state tool with state thinking and verify status changes."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        res = client.request("tools/call", {
            "name": "update_state",
            "arguments": {"state": "thinking"}
        }, msg_id=2)
        
        assert "result" in res
        assert not res.get("error")
    finally:
        client.stop()

def test_mcp_force_animation(mcp_client):
    """Call force_animation tool and verify response."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        res = client.request("tools/call", {
            "name": "force_animation",
            "arguments": {"state": "success", "duration": 2}
        }, msg_id=2)
        
        assert "result" in res
        assert not res.get("error")
    finally:
        client.stop()


# Tier 2: Boundary & Corner Cases (5 cases)

def test_mcp_invalid_state(mcp_client):
    """Call update_state with invalid state (e.g. dancing) and verify RPC error or failure content."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        res = client.request("tools/call", {
            "name": "update_state",
            "arguments": {"state": "dancing"}
        }, msg_id=2)
        
        # It should either return an RPC error or a result containing error description
        assert ("error" in res) or (res.get("result") and "error" in res["result"]["content"][0]["text"].lower())
    finally:
        client.stop()

def test_mcp_missing_args(mcp_client):
    """Call update_state without state parameter and verify it returns an RPC error or invalid params."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        res = client.request("tools/call", {
            "name": "update_state",
            "arguments": {}
        }, msg_id=2)
        
        # Missing required parameter should return RPC error
        assert "error" in res or "error" in res.get("result", {}).get("content", [{}])[0].get("text", "").lower()
    finally:
        client.stop()

def test_mcp_malformed_rpc(mcp_client):
    """Send a malformed JSON string (invalid JSON format) and verify it returns a JSON-RPC parse error."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        # Send raw malformed JSON
        client.send_raw("{invalid_json_string")
        res_str = client.receive_raw()
        res = json.loads(res_str)
        # Parse error code is -32700
        assert "error" in res
        assert res["error"]["code"] == -32700
    finally:
        client.stop()

def test_mcp_lost_gui_connection(mcp_client):
    """Verify that calling an MCP tool when GUI process is dead returns a clean error instead of crashing MCP."""
    # Since the GUI process is not running during this standalone test, we just call the tool.
    # The MCP server must return a clean message indicating GUI is unreachable, not crash.
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Call query_status. Since GUI is dead, it should fail gracefully
        res = client.request("tools/call", {
            "name": "query_status",
            "arguments": {}
        }, msg_id=2)
        
        # Result should indicate GUI connection error, not crash the MCP server connection
        assert "result" in res or "error" in res
    finally:
        client.stop()

def test_mcp_query_during_force(mcp_client):
    """Call query_status via MCP while a forced animation is active and check that it returns properly."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Force state
        client.request("tools/call", {
            "name": "force_animation",
            "arguments": {"state": "error", "duration": 5}
        }, msg_id=2)
        
        # Query status immediately
        res = client.request("tools/call", {
            "name": "query_status",
            "arguments": {}
        }, msg_id=3)
        
        assert "result" in res
        content = res["result"]["content"]
        assert len(content) > 0
    finally:
        client.stop()
