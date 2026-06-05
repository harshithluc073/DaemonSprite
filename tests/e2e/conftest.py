import os
import sys
import json
import socket
import time
import subprocess
import pytest

# Ensure QT_QPA_PLATFORM is offscreen for headless Qt runs
os.environ["QT_QPA_PLATFORM"] = "offscreen"

class MockMCPClient:
    """Mock MCP Client communicating over stdio transport."""
    def __init__(self, command, cwd=None):
        self.command = command
        self.cwd = cwd
        self.process = None

    def start(self):
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.cwd,
            env=os.environ.copy()
        )

    def send_raw(self, payload_str):
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP Server process is not running.")
        self.process.stdin.write(payload_str + "\n")
        self.process.stdin.flush()

    def receive_raw(self, timeout=5.0):
        # We can implement a simple line read
        line = self.process.stdout.readline()
        if not line:
            err = self.process.stderr.read()
            raise RuntimeError(f"Server exited or closed stdout. Stderr: {err}")
        return line.strip()

    def request(self, method, params=None, msg_id=1):
        payload = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method
        }
        if params is not None:
            payload["params"] = params
        self.send_raw(json.dumps(payload))
        response_str = self.receive_raw()
        return json.loads(response_str)

    def notify(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            payload["params"] = params
        self.send_raw(json.dumps(payload))

    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


class TCPClientHelper:
    """Helper for communicating with the Daemon GUI TCP server."""
    def __init__(self, host="127.0.0.1", port=18374):
        self.host = host
        self.port = port

    def send_command(self, cmd_dict, timeout=1.0):
        with socket.create_connection((self.host, self.port), timeout=timeout) as sock:
            sock.sendall((json.dumps(cmd_dict) + "\n").encode("utf-8"))
            response = sock.recv(4096).decode("utf-8")
            return json.loads(response.strip())


@pytest.fixture
def mcp_client():
    def _create_client(command, cwd=None):
        client = MockMCPClient(command, cwd)
        return client
    return _create_client


@pytest.fixture
def tcp_client():
    def _create_client(host="127.0.0.1", port=18374):
        return TCPClientHelper(host, port)
    return _create_client
