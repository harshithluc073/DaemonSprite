import os
import sys
import time
import subprocess
import socket
import pytest
from PySide6.QtCore import Qt

try:
    from src.daemon_gui import DaemonWindow
except ImportError:
    DaemonWindow = None

# Feature 1: Windowing (F1)

# Tier 1: Feature Coverage (5 cases)

def test_gui_launch():
    """Verify that the GUI process starts successfully, binds to the TCP port, and exits cleanly."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    proc = subprocess.Popen(
        [sys.executable, gui_path],
        env={"QT_QPA_PLATFORM": "offscreen", **os.environ}
    )
    
    # Check if TCP port 18374 is bound
    connected = False
    for _ in range(10):
        try:
            with socket.create_connection(("127.0.0.1", 18374), timeout=0.5):
                connected = True
                break
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
            
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        
    assert connected, "GUI did not start or bind to TCP port 18374."

def test_gui_frameless(qtbot):
    """Verify GUI window has FramelessWindowHint flag."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
    
    window = DaemonWindow()
    qtbot.addWidget(window)
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint

def test_gui_transparency(qtbot):
    """Verify GUI window background is translucent."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

def test_gui_always_on_top(qtbot):
    """Verify GUI window has WindowStaysOnTopHint flag."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint

def test_gui_click_through(qtbot):
    """Verify GUI window attribute or flags for mouse click-through are set."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    # Check for mouse event transparency
    assert window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


# Tier 2: Boundary & Corner Cases (5 cases)

def test_gui_resize_limits(qtbot):
    """Verify that the GUI window has fixed sizing matching the sprite sizes and cannot be resized."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    
    # Assert minimum and maximum sizes are equal (fixed size)
    assert window.minimumSize() == window.maximumSize()
    assert window.minimumWidth() > 0
    assert window.minimumHeight() > 0

def test_gui_offscreen_position(qtbot):
    """Verify window behaves gracefully and doesn't crash when positioned offscreen."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    window.move(-1000, -1000)
    window.show()
    # Should not crash and should register coordinates
    assert window.x() == -1000
    assert window.y() == -1000

def test_gui_display_change(qtbot):
    """Verify window handles screen/display boundary query without crash."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    screen = window.screen()
    assert screen is not None
    geom = screen.geometry()
    assert geom.width() > 0
    assert geom.height() > 0

def test_gui_focus_lost(qtbot):
    """Verify window retains translucency, frameless and always-on-top attributes when focus is lost."""
    if DaemonWindow is None:
        pytest.fail("DaemonWindow could not be imported.")
        
    window = DaemonWindow()
    qtbot.addWidget(window)
    window.show()
    
    # Simulate focus lost event
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtCore import QEvent
    event = QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.ActiveWindowFocusReason)
    sys.modules['PySide6'].QtWidgets.QApplication.sendEvent(window, event)
    
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

def test_gui_port_in_use():
    """Verify second GUI instance exits cleanly or throws when port 18374 is already bound."""
    gui_path = os.path.join("src", "daemon_gui.py")
    if not os.path.exists(gui_path):
        pytest.fail(f"GUI script {gui_path} not found.")

    # Bind the port ourselves to simulate it being in use
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 18374))
        s.listen(1)
    except OSError:
        # Port already bound by another process
        s.close()
        pytest.fail("Cannot run test because port 18374 is already bound by system.")
        
    try:
        # Run GUI process
        proc = subprocess.Popen(
            [sys.executable, gui_path],
            env={"QT_QPA_PLATFORM": "offscreen", **os.environ},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # It should exit with a non-zero code or log port failure and exit within 5s
        try:
            ret = proc.wait(timeout=5.0)
            assert ret != 0, "Second GUI process should fail to run and exit with non-zero code."
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()
            pytest.fail("GUI process did not exit when port was in use.")
    finally:
        s.close()
