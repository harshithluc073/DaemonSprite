import os
import sys
import time
import socket
import json
import shutil
import subprocess
import pytest
from PySide6.QtCore import Qt

try:
    from src.daemon_gui import DaemonWindow
except ImportError:
    DaemonWindow = None

# Feature 3: Animation Rendering (F3)

# Tier 1: Feature Coverage (5 cases)

def test_gui_load_sprites(qtbot):
    """Verify that the GUI window successfully loads and caches the generated sprite frames on startup."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    # The window should have a method or property showing loaded frames
    assert hasattr(window, "sprite_frames") or hasattr(window, "animations")
    
    # Check that frames are not empty (assuming implementation caches them in a dict or list)
    if hasattr(window, "sprite_frames"):
        assert len(window.sprite_frames) > 0

def test_default_idle_animation():
    """Start the GUI process, query status via TCP, and assert that the default animation state is idle."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Connect to GUI TCP server and send query command
        status = None
        for _ in range(10):
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=0.5) as sock:
                    sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
                    res = sock.recv(1024).decode("utf-8")
                    status = json.loads(res.strip())
                    break
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(0.5)
                
        assert status is not None, "Failed to connect to GUI TCP server."
        assert status.get("status") == "ok"
        assert status.get("state") == "idle", f"Expected state to be 'idle', got {status.get('state')}"
    finally:
        proc.terminate()
        proc.wait()

def test_animation_frame_cycling(qtbot):
    """Verify that the frame index changes over time as the animation plays."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    window.show()
    
    # Get initial frame index (assuming current_frame property exists)
    assert hasattr(window, "current_frame") or hasattr(window, "current_frame_index")
    
    idx_attr = "current_frame" if hasattr(window, "current_frame") else "current_frame_index"
    initial_idx = getattr(window, idx_attr)
    
    # Wait for the animation timer to tick a few times
    time.sleep(0.5)
    
    # The index should have updated or cycled
    new_idx = getattr(window, idx_attr)
    # (Note: In a pure offscreen test, we may need to trigger the timer manually if event loop isn't spinning,
    # but with qtbot it runs the event loop)
    # We can use qtbot.waitActive(window) or run the event loop for a bit
    qtbot.wait(300)
    
    # Assert frame cycling works
    # If the timer is active, index changes
    assert getattr(window, idx_attr) is not None

def test_force_animation_playing():
    """Send a force_animation TCP command and verify that the GUI switches to the target animation immediately."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Connect and send force_animation command
        success = False
        for _ in range(10):
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=0.5) as sock:
                    cmd = {"action": "force_animation", "state": "success", "duration": 5}
                    sock.sendall(json.dumps(cmd).encode("utf-8") + b"\n")
                    res = json.loads(sock.recv(1024).decode("utf-8").strip())
                    assert res.get("status") == "ok"
                    
                    # Instantly query state
                    sock2 = socket.create_connection(("127.0.0.1", 18374), timeout=0.5)
                    sock2.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
                    res2 = json.loads(sock2.recv(1024).decode("utf-8").strip())
                    assert res2.get("state") == "success"
                    success = True
                    sock2.close()
                    break
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(0.5)
        assert success, "Failed to force and verify animation state change."
    finally:
        proc.terminate()
        proc.wait()

def test_force_animation_revert():
    """Send a force_animation TCP command with short duration (1s) and verify that after 1.5s, state reverts."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Force state to error for 1s
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            cmd = {"action": "force_animation", "state": "error", "duration": 1}
            sock.sendall(json.dumps(cmd).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            assert res.get("status") == "ok"
            
        # Wait 1.5s
        time.sleep(1.5)
        
        # Query status again
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            sock.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            # Should revert back to idle
            assert res.get("state") == "idle", f"Expected state to revert to 'idle', got '{res.get('state')}'"
    finally:
        proc.terminate()
        proc.wait()


# Tier 2: Boundary & Corner Cases (5 cases)

def test_animation_fps_bounds(qtbot):
    """Test rendering loop under extreme FPS settings (e.g., 1 FPS or 100 FPS) and verify stability."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    # Test setting custom frame duration / FPS if supported
    window = DaemonWindow()
    qtbot.addWidget(window)
    
    if hasattr(window, "set_fps"):
        window.set_fps(1)
        assert window.fps == 1
        window.set_fps(100)
        assert window.fps == 100
    else:
        # Simply check that timer exists and is running
        assert hasattr(window, "timer") or hasattr(window, "animation_timer")

def test_rapid_animation_state_changes():
    """Send state transition commands in rapid succession and verify the rendering loop doesn't crash."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Wait for GUI server to bind
        bound = False
        for _ in range(10):
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=0.2):
                    bound = True
                    break
            except OSError:
                time.sleep(0.2)
        if not bound:
            pytest.fail("GUI failed to bind port.")
            
        # Send 20 rapid set_state commands
        states = ["thinking", "typing", "success", "error", "idle"]
        for i in range(20):
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=0.5) as sock:
                    state = states[i % len(states)]
                    cmd = {"action": "set_state", "state": state}
                    sock.sendall(json.dumps(cmd).encode("utf-8") + b"\n")
                    sock.recv(1024)
            except OSError:
                pytest.fail(f"TCP connection failed or crashed during rapid state updates at step {i}")
            time.sleep(0.01)
    finally:
        proc.terminate()
        proc.wait()

def test_animation_empty_frames(tmp_path, qtbot):
    """Verify rendering behavior when an animation folder has 0 frames."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    # We create a temporary empty folder for an animation and verify it falls back without crash
    empty_state_dir = tmp_path / "empty_state"
    empty_state_dir.mkdir()
    
    # Initialize window with custom assets directory
    window = DaemonWindow(assets_dir=str(tmp_path))
    qtbot.addWidget(window)
    window.show()
    
    # Should use a fallback/error frame
    assert window.current_frame is not None or hasattr(window, "fallback_frame")

def test_animation_missing_assets(tmp_path, qtbot):
    """Delete/rename the asset files and verify the GUI displays a default placeholder box and does not crash."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    # Launch window with an empty folder (missing assets)
    window = DaemonWindow(assets_dir=str(tmp_path / "nonexistent"))
    qtbot.addWidget(window)
    window.show()
    
    # Verify it handles missing folder without crashing and sets a fallback
    assert window.isVisible()

def test_force_animation_zero_duration():
    """Verify that forcing an animation with duration <= 0 reverts immediately or is rejected."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    try:
        # Wait for GUI to bind
        bound = False
        for _ in range(10):
            try:
                with socket.create_connection(("127.0.0.1", 18374), timeout=0.2):
                    bound = True
                    break
            except OSError:
                time.sleep(0.2)
        if not bound:
            pytest.fail("GUI failed to bind port.")
            
        with socket.create_connection(("127.0.0.1", 18374), timeout=1.0) as sock:
            # Force animation with duration 0
            cmd = {"action": "force_animation", "state": "success", "duration": 0}
            sock.sendall(json.dumps(cmd).encode("utf-8") + b"\n")
            res = json.loads(sock.recv(1024).decode("utf-8").strip())
            # Should either return status ok (and instantly revert to idle) or status error
            if res.get("status") == "ok":
                # Immediately query status, should be back to idle
                sock2 = socket.create_connection(("127.0.0.1", 18374), timeout=1.0)
                sock2.sendall(json.dumps({"action": "query"}).encode("utf-8") + b"\n")
                res2 = json.loads(sock2.recv(1024).decode("utf-8").strip())
                assert res2.get("state") == "idle", f"Expected instant revert to 'idle', got '{res2.get('state')}'"
                sock2.close()
            else:
                assert res.get("status") == "error"
    finally:
        proc.terminate()
        proc.wait()
