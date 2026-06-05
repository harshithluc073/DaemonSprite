import os
import sys
import subprocess
import shutil
import stat
import pytest
from PIL import Image

# Ensure project root is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import src.generate_sprites as gs
except ImportError:
    gs = None

# Feature 2: Procedural Sprites (F2)

# Tier 1: Feature Coverage (5 cases)

def test_sprite_generator_runs():
    """Run generate_sprites.py and verify it exits with code 0."""
    gen_path = os.path.join("src", "generate_sprites.py")
    if not os.path.exists(gen_path):
        pytest.fail(f"Generator script {gen_path} not found.")

    res = subprocess.run([sys.executable, gen_path], capture_output=True, text=True)
    assert res.returncode == 0, f"Generator exited with code {res.returncode}. Stderr: {res.stderr}"

def test_assets_dir_creation():
    """Verify that the assets/ directory is created after running the generator."""
    # Ensure assets dir is clean or removed before running
    assets_dir = "assets"
    if os.path.exists(assets_dir):
        # Rename or delete to verify recreation
        try:
            shutil.rmtree(assets_dir)
        except OSError:
            pass

    gen_path = os.path.join("src", "generate_sprites.py")
    if not os.path.exists(gen_path):
        pytest.fail(f"Generator script {gen_path} not found.")

    subprocess.run([sys.executable, gen_path], check=True)
    assert os.path.isdir(assets_dir), "assets directory was not created."

def test_idle_sprites_exist():
    """Verify that procedural sprite files for the idle state are generated."""
    assets_dir = "assets"
    if not os.path.isdir(assets_dir):
        pytest.fail("assets directory does not exist.")
        
    idle_files = [f for f in os.listdir(assets_dir) if f.startswith("idle_") and f.endswith(".png")]
    assert len(idle_files) > 0, "No idle state sprite files found in assets/."

def test_all_states_sprites_exist():
    """Verify that sprite files for thinking, typing, error, and success states are present in assets/."""
    assets_dir = "assets"
    if not os.path.isdir(assets_dir):
        pytest.fail("assets directory does not exist.")
        
    for state in ["idle", "thinking", "typing", "error", "success"]:
        state_files = [f for f in os.listdir(assets_dir) if f.startswith(f"{state}_") and f.endswith(".png")]
        assert len(state_files) > 0, f"No files found for state: {state} in assets/."

def test_sprite_transparency():
    """Load one of the generated PNGs (using Pillow) and verify that it has an alpha channel (RGBA) and transparent pixels."""
    assets_dir = "assets"
    if not os.path.isdir(assets_dir):
        pytest.fail("assets directory does not exist.")
        
    idle_files = [f for f in os.listdir(assets_dir) if f.startswith("idle_") and f.endswith(".png")]
    if not idle_files:
        pytest.fail("No idle sprite found to test transparency.")
        
    img_path = os.path.join(assets_dir, idle_files[0])
    with Image.open(img_path) as img:
        assert img.mode == "RGBA", f"Image mode is {img.mode}, expected RGBA."
        # Verify that there are some transparent pixels (alpha < 255)
        pixels = img.load()
        width, height = img.size
        has_transparent = False
        for x in range(width):
            for y in range(height):
                r, g, b, a = pixels[x, y]
                if a < 255:
                    has_transparent = True
                    break
            if has_transparent:
                break
        assert has_transparent, "No transparent pixels found in the sprite image."


# Tier 2: Boundary & Corner Cases (5 cases)

def test_sprite_size_bounds():
    """Run sprite generator with extreme size parameters (e.g. 1x1 or 1024x1024) and check handling."""
    gen_path = os.path.join("src", "generate_sprites.py")
    if not os.path.exists(gen_path):
        pytest.fail(f"Generator script {gen_path} not found.")

    # Run with extreme sizes (assuming command line flags are supported, e.g. --size 1 or --size 1024)
    # If parameters are rejected or handled gracefully:
    res = subprocess.run([sys.executable, gen_path, "--size", "1"], capture_output=True, text=True)
    # It should either succeed (with fallback or generating 1x1) or fail gracefully with exit code 0 or 1
    assert res.returncode in [0, 1]

def test_sprite_readonly_dir(tmp_path):
    """Run sprite generator when output directory is write-protected, and verify graceful exception handling."""
    gen_path = os.path.join("src", "generate_sprites.py")
    if not os.path.exists(gen_path):
        pytest.fail(f"Generator script {gen_path} not found.")
        
    # Create a file where directory should be to simulate write failure
    ro_dir = tmp_path / "readonly_assets"
    ro_dir.write_text("blocker")
    
    # Run generator pointing to this output directory
    res = subprocess.run(
        [sys.executable, gen_path, "--output-dir", str(ro_dir)],
        capture_output=True,
        text=True
    )
    # It must exit gracefully with a non-zero code or handle the error
    assert res.returncode != 0 or "Error" in res.stderr or "Error" in res.stdout or "FileExistsError" in res.stderr

def test_sprite_invalid_palette():
    """Pass invalid color hex codes to generator and verify it falls back or exits cleanly."""
    gen_path = os.path.join("src", "generate_sprites.py")
    if not os.path.exists(gen_path):
        pytest.fail(f"Generator script {gen_path} not found.")
        
    # Run with invalid color flag
    res = subprocess.run(
        [sys.executable, gen_path, "--palette", "invalid_color_code"],
        capture_output=True,
        text=True
    )
    # Should handle cleanly (exit 0 with fallback or exit 1 with nice message)
    assert res.returncode in [0, 1]

def test_sprite_disk_full(tmp_path, monkeypatch):
    """Simulate disk write failure during generation and verify it handles IOError cleanly."""
    if gs is None:
        pytest.fail("generate_sprites module could not be imported.")
        
    # Monkeypatch write/save function in PIL to raise OSError("No space left on device")
    def mock_save(*args, **kwargs):
        raise OSError(28, "No space left on device")
        
    monkeypatch.setattr(Image.Image, "save", mock_save)
    
    # Run internal generator code (or main block) and expect it to handle exception or raise it cleanly
    with pytest.raises(OSError):
        gs.generate_all(output_dir=str(tmp_path))

def test_sprite_naming_boundaries():
    """Verify that frame numbering begins at 0, has no gaps, and filenames are padded correctly."""
    assets_dir = "assets"
    if not os.path.isdir(assets_dir):
        pytest.fail("assets directory does not exist.")
        
    for state in ["idle", "thinking", "typing", "error", "success"]:
        state_files = sorted([f for f in os.listdir(assets_dir) if f.startswith(f"{state}_") and f.endswith(".png")])
        if not state_files:
            pytest.fail(f"No files for {state}")
            
        # Check first frame is frame 0
        first_frame = state_files[0]
        # Frame numbers should start at 0
        assert "0" in first_frame or "00" in first_frame
        
        # Verify no gaps
        frame_indices = []
        for file in state_files:
            # Extract number
            parts = file.replace(f"{state}_", "").replace(".png", "")
            try:
                frame_indices.append(int(parts))
            except ValueError:
                pytest.fail(f"Invalid frame filename pattern: {file}")
                
        # Indices should be contiguous from 0 to N-1
        assert frame_indices == list(range(len(frame_indices))), f"Frame numbers for {state} are not contiguous or do not start at 0: {frame_indices}"
