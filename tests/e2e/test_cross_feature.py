import os
import sys
import time
import socket
import json
import subprocess
import pytest
from PySide6.QtCore import Qt

try:
    from src.daemon_gui import DaemonWindow
except ImportError:
    DaemonWindow = None

# Tier 3: Cross-Feature Combinations (5 cases)

def test_mcp_to_gui_state_propagation(mcp_client):
    """Updating state via MCP server stdio tool call sends a TCP message to GUI and changes visible state."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    # Start GUI
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    # Wait for GUI port to bind
    time.sleep(1.0)
    
    # Start MCP server
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        # Initialize MCP
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Call update_state tool -> "typing"
        client.request("tools/call", {
            "name": "update_state",
            "arguments": {"state": "typing"}
        }, msg_id=2)
        
        # Query GUI state via TCP directly
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("state") == "typing"
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_generated_sprites_loaded_in_gui():
    """Test that procedurally generated sprites are correctly loaded by the GUI and rendered."""
    gui_path = os.path.join("src", "daemon_gui.py")
    gen_path = os.path.join("src", "generate_sprites.py")
    if not (os.path.exists(gui_path) and os.path.exists(gen_path)):
        pytest.fail("GUI or Generator script missing.")
        
    # 1. Run sprite generator
    subprocess.run([sys.executable, gen_path], check=True)
    
    # 2. Launch GUI
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Wait for GUI port to bind
        time.sleep(1.0)
        
        # Query status via TCP
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("status") == "ok"
            # It starts in idle and lists idle frames loaded
            assert res.get("state") == "idle"
    finally:
        gui_proc.terminate()
        gui_proc.wait()

def test_mcp_force_animation_duration_rendering(mcp_client):
    """Calling force_animation via MCP changes GUI state for specified duration, then returns to base state."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    # Start GUI
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    time.sleep(1.0)
    
    # Start MCP server
    client = mcp_client([sys.executable, mcp_path])
    client.start()
    
    try:
        # Initialize MCP
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Call force_animation via MCP for 2s
        client.request("tools/call", {
            "name": "force_animation",
            "arguments": {"state": "error", "duration": 2}
        }, msg_id=2)
        
        # Verify GUI state is error
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("state") == "error"
            
        # Wait 2.5s
        time.sleep(2.5)
        
        # Verify GUI state is back to idle
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("state") == "idle"
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_custom_port_binding(mcp_client):
    """Launch GUI on custom port X and MCP server pointing to port X, and verify connection."""
    gui_path = os.path.join("src", "daemon_gui.py")
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not (os.path.exists(gui_path) and os.path.exists(mcp_path)):
        pytest.fail("GUI or MCP script missing.")
        
    custom_port = 19123
    
    # Start GUI on custom port
    gui_proc = subprocess.Popen(
        [sys.executable, gui_path, "--port", str(custom_port)],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    # Wait for binding
    time.sleep(1.0)
    
    # Start MCP server pointing to custom port
    client = mcp_client([sys.executable, mcp_path, "--gui-port", str(custom_port)])
    client.start()
    
    try:
        # Initialize MCP
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-runner", "version": "1.0.0"}
        }, msg_id=1)
        client.notify("notifications/initialized")
        
        # Call query_status tool to verify it accesses the correct port
        res = client.request("tools/call", {
            "name": "query_status",
            "arguments": {}
        }, msg_id=2)
        assert "result" in res
        
        # Query GUI directly on custom port
        with socket.create_connection(("127.0.0.1", custom_port), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("status") == "ok"
            
    finally:
        client.stop()
        gui_proc.terminate()
        gui_proc.wait()

def test_gui_rendering_during_window_events(qtbot):
    """Verify GUI animation loop runs normally even when window focus is lost or gained."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    window.show()
    
    # Verify timer is running
    assert window.timer.isActive()
    
    # Simulate window focus lost
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtCore import QEvent
    event_out = QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.ActiveWindowFocusReason)
    sys.modules['PySide6'].QtWidgets.QApplication.sendEvent(window, event_out)
    
    # Timer should still be active
    assert window.timer.isActive()
    
    # Simulate window focus gained
    event_in = QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.ActiveWindowFocusReason)
    sys.modules['PySide6'].QtWidgets.QApplication.sendEvent(window, event_in)
    
    # Timer should still be active
    assert window.timer.isActive()
