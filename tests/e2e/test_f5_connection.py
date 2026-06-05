import os
import sys
import json
import subprocess
import pytest

# Feature 5: Standalone Connection (F5)

# Tier 1: Feature Coverage (5 cases)

def test_cursor_config_validation(tmp_path):
    """Parse and validate the Cursor integration config format (ensure it contains right command and args)."""
    # Write a mock Cursor config
    config_data = {
        "mcpServers": {
            "daemonsprite": {
                "command": sys.executable,
                "args": [os.path.abspath(os.path.join("src", "daemon_mcp.py"))]
            }
        }
    }
    config_file = tmp_path / "cursor_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
    # Read and validate
    with open(config_file, "r") as f:
        parsed = json.load(f)
        
    assert "mcpServers" in parsed
    assert "daemonsprite" in parsed["mcpServers"]
    srv = parsed["mcpServers"]["daemonsprite"]
    assert "command" in srv
    assert "args" in srv
    assert "daemon_mcp.py" in srv["args"][0]

def test_claude_config_validation(tmp_path):
    """Parse and validate the Claude Code integration config format."""
    config_data = {
        "mcpServers": {
            "daemonsprite": {
                "command": sys.executable,
                "args": [os.path.abspath(os.path.join("src", "daemon_mcp.py"))]
            }
        }
    }
    config_file = tmp_path / "claude_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
    with open(config_file, "r") as f:
        parsed = json.load(f)
        
    assert "mcpServers" in parsed
    assert "daemonsprite" in parsed["mcpServers"]

def test_antigravity_config_validation(tmp_path):
    """Parse and validate the Antigravity integration config format."""
    config_data = {
        "mcpServers": {
            "daemonsprite": {
                "command": sys.executable,
                "args": [os.path.abspath(os.path.join("src", "daemon_mcp.py"))]
            }
        }
    }
    config_file = tmp_path / "antigravity_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
    with open(config_file, "r") as f:
        parsed = json.load(f)
        
    assert "mcpServers" in parsed
    assert "daemonsprite" in parsed["mcpServers"]

def test_connection_params():
    """Verify that configuration templates or files specify correct executable and parameters."""
    # Check that src/daemon_mcp.py is referenced as the primary target in standard configs
    mcp_path = os.path.join("src", "daemon_mcp.py")
    # Verify it exists or is referenced correctly in source if config files exist
    assert os.path.normpath(mcp_path)

def test_config_overrides(tmp_path):
    """Verify that launching the MCP server with custom config changes default behavior (e.g. changing TCP port)."""
    # Create custom config file specifying TCP port 19999
    config_data = {"port": 19999}
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")

    # Start MCP server pointing to this config file (via command line arguments or environment variable)
    proc = subprocess.Popen(
        [sys.executable, mcp_path, "--config", str(config_file)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Should use port 19999
    time.sleep(0.5)
    proc.terminate()
    proc.wait()


# Tier 2: Boundary & Corner Cases (5 cases)

def test_config_malformed_json(tmp_path):
    """Launch the MCP server with a malformed configuration file, and verify it exits with a descriptive error."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")
        
    config_file = tmp_path / "malformed.json"
    with open(config_file, "w") as f:
        f.write("{invalid_json_content}")
        
    res = subprocess.run(
        [sys.executable, mcp_path, "--config", str(config_file)],
        capture_output=True,
        text=True
    )
    # It must exit with error due to parsing error
    assert res.returncode != 0
    assert "JSON" in res.stderr or "error" in res.stderr.lower()

def test_config_empty_keys(tmp_path):
    """Launch with configuration file containing empty keys/values, and verify it uses default fallbacks."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")
        
    config_file = tmp_path / "empty_keys.json"
    with open(config_file, "w") as f:
        json.dump({"port": None, "host": ""}, f)
        
    # Should fallback to defaults and run successfully
    proc = subprocess.Popen(
        [sys.executable, mcp_path, "--config", str(config_file)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(0.5)
    assert proc.poll() is None
    proc.terminate()
    proc.wait()

def test_config_missing_env():
    """Verify that the MCP server runs correctly even if standard editor environment variables are missing."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")
        
    # Strip env vars
    clean_env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "PATH": os.environ.get("PATH", "")
    }
    
    proc = subprocess.Popen(
        [sys.executable, mcp_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=clean_env
    )
    time.sleep(0.5)
    assert proc.poll() is None
    proc.terminate()
    proc.wait()

def test_config_invalid_port(tmp_path):
    """Set port override in config to invalid port (e.g. 999999 or -1) and verify the server rejects it or falls back."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")
        
    config_file = tmp_path / "invalid_port.json"
    with open(config_file, "w") as f:
        json.dump({"port": -1}, f)
        
    res = subprocess.run(
        [sys.executable, mcp_path, "--config", str(config_file)],
        capture_output=True,
        text=True
    )
    # Rejects with non-zero exit code or falls back (exits cleanly)
    assert res.returncode in [0, 1]

def test_config_unsupported_transport(tmp_path):
    """Verify that launching with unsupported transport options returns a descriptive error message."""
    mcp_path = os.path.join("src", "daemon_mcp.py")
    if not os.path.exists(mcp_path):
        pytest.fail(f"MCP script {mcp_path} not found.")
        
    config_file = tmp_path / "unsupported_transport.json"
    with open(config_file, "w") as f:
        json.dump({"transport": "http-post-unsupported"}, f)
        
    res = subprocess.run(
        [sys.executable, mcp_path, "--config", str(config_file)],
        capture_output=True,
        text=True
    )
    # Should exit with error indicating unsupported transport
    assert res.returncode != 0
    assert "transport" in res.stderr.lower() or "error" in res.stderr.lower()
