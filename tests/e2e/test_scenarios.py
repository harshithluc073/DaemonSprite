import os
import sys
import time
import socket
import json
import subprocess
import pytest

# Tier 4: Real-World Application Scenarios (5 cases)

def test_scenario_cursor_coding_flow(mcp_client):
    """Simulate Cursor editing cycle: Idle -> Typing -> Thinking -> Success (3s) -> Idle."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    time.sleep(1.0)
    
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # 1. Start in idle - verify
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "idle"
            
        # 2. User types prompt (MCP state -> typing)
        client.request("tools/call", {
            "name": "update_state",
            "arguments": {"state": "typing"}
        }, msg_id=2)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "typing"
            
        # 3. Model thinks (MCP state -> thinking)
        client.request("tools/call", {
            "name": "update_state",
            "arguments": {"state": "thinking"}
        }, msg_id=3)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "thinking"
            
        # 4. Model edits successfully (force_animation success for 2s)
        client.request("tools/call", {
            "name": "force_animation",
            "arguments": {"state": "success", "duration": 2}
        }, msg_id=4)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "success"
            
        # 5. Wait 2.5s -> returns to idle
        time.sleep(2.5)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "idle"
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_scenario_error_recovery(mcp_client):
    """Simulate a compile error: Idle -> Error (2s) -> Idle."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    time.sleep(1.0)
    
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Command runs and fails -> force_animation error for 2s
        client.request("tools/call", {
            "name": "force_animation",
            "arguments": {"state": "error", "duration": 2}
        }, msg_id=2)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "error"
            
        # Wait 2.5s -> returns to idle
        time.sleep(2.5)
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
            s.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            assert json.loads(s.recv(1024).decode("utf-8").strip()).get("state") == "idle"
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_scenario_rapid_tool_interleaving(mcp_client):
    """Simulate rapid tool runs from Claude Code and verify order and no TCP overflows."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    time.sleep(1.0)
    
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Rapid tool interleaving
        for i in range(10):
            res_query = client.request("tools/call", {"name": "query_status", "arguments": {}}, msg_id=10+i*3)
            assert "result" in res_query
            
            res_update = client.request("tools/call", {"name": "update_state", "arguments": {"state": "typing"}}, msg_id=11+i*3)
            assert "result" in res_update
            
            res_query2 = client.request("tools/call", {"name": "query_status", "arguments": {}}, msg_id=12+i*3)
            assert "result" in res_query2
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_scenario_long_lifespan(mcp_client):
    """Simulate a long lifespan with 100 continuous status/update calls to verify stability."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    time.sleep(1.0)
    
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # 100 continuous updates
        states = ["idle", "thinking", "typing", "success", "error"]
        for i in range(100):
            res = client.request("tools/call", {
                "name": "update_state",
                "arguments": {"state": states[i % len(states)]}
            }, msg_id=100+i)
            assert "result" in res
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_scenario_process_restart_stress(mcp_client):
    """Stress test process restarts and clean termination.
    Start MCP -> GUI spawns. Terminate GUI -> MCP recreates it on next tool call. Terminate MCP -> GUI exits.
    """
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    # Standard MCP server command should spawn GUI automatically on tool call or startup
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        for cycle in range(3):  # Repeat 3 times to stress-test
            # Initialize
            client.request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-runner", "version": "1.0.0"}
            }, msg_id=1000 + cycle * 10)
            client.notify("notifications/initialized")
            
            # Call a tool to ensure GUI is spawned and listening
            client.request("tools/call", {
                "name": "query_status",
                "arguments": {}
            }, msg_id=1001 + cycle * 10)
            
            # Find and terminate the spawned GUI process
            # (In a real implementation, the MCP process spawns and tracks the GUI process.
            # We can query standard ports or look up Python processes, or wait for next tool call to auto-recreate)
            # Send command via TCP to GUI to self-terminate (simulating crash)
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as s:
                    s.sendall(json.dumps({"action": "self_terminate"}).encode("utf-8") + b"\n")
            except OSError:
                pass  # It might already be stopped
                
            time.sleep(0.5)
            
            # Next tool call on MCP should auto-recreate the GUI process and succeed
            res = client.request("tools/call", {
                "name": "query_status",
                "arguments": {}
            }, msg_id=1002 + cycle * 10)
            assert "result" in res
            
    finally:
        client.stop()
        # Terminating MCP should automatically clean up and terminate the GUI
        time.sleep(1.0)
        # Check that port 18374 is free now
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 18374))
            s.close()
        except OSError:
            s.close()
            pytest.fail("GUI process did not exit cleanly when MCP server was terminated.")
