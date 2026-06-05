import os
import argparse
import sys
from PIL import Image, ImageDraw

def create_sprite(state, frame_idx, size=128):
    """
    Procedurally draws a cute, original pixel-art style sprite for a given state and frame index.
    Draws on a 32x32 canvas, and scales up to `size` using NEAREST resampler to keep the pixel grid clean.
    """
    base_size = (32, 32)
    img = Image.new("RGBA", base_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outline and body colors
    outline_color = (30, 10, 50, 255)
    horn_outline = outline_color
    eye_outline = outline_color
    
    # Defaults
    body_color = (123, 44, 191, 255) # Deep purple
    horn_color = (255, 112, 166, 255) # Pink
    
    offset_x = 0
    offset_y = 0
    squash_h = 0
    squash_w = 0
    
    # Success State: Green, jumping, smiling with arch eyes, sparkles
    if state == "success":
        body_color = (39, 174, 96, 255) # Green
        horn_color = (241, 196, 15, 255) # Gold/Yellow
        jump_offsets = [0, -2, -4, -1]
        offset_y = jump_offsets[frame_idx % 4]
        
    # Error State: Flashing red/orange, shaking, crossed-out eyes, screaming mouth
    elif state == "error":
        red_shades = [
            (230, 57, 70, 255),  # Hot red
            (241, 135, 1, 255),  # Orange-red
            (180, 20, 50, 255),  # Deep blood red
            (255, 80, 80, 255)   # Light red
        ]
        body_color = red_shades[frame_idx % len(red_shades)]
        horn_color = (30, 10, 50, 255) # Dark horns
        
        # Shake/Jitter offsets
        shake_offsets = [(-1, 0), (1, -1), (0, 1), (-1, -1)]
        offset_x, offset_y = shake_offsets[frame_idx % len(shake_offsets)]
        
    # Idle State: Breathing squash/stretch, blinking eyes
    elif state == "idle":
        if frame_idx % 4 == 1 or frame_idx % 4 == 3:
            squash_h = -1
            squash_w = 1
            offset_y = 1
        elif frame_idx % 4 == 2:
            squash_h = -2
            squash_w = 2
            offset_y = 2
            
    # Base dimensions for body box: left, top, right, bottom
    b_left = 6 - squash_w + offset_x
    b_top = 10 - squash_h + offset_y
    b_right = 25 + squash_w + offset_x
    b_bottom = 27 + offset_y
    
    # 1. Draw Body Outline
    draw.ellipse([b_left - 1, b_top - 1, b_right + 1, b_bottom + 1], fill=outline_color)
    
    # 2. Draw Horn Outlines & Fills
    # Left horn
    lh_outline = [
        (b_left + 1, b_top),
        (b_left + 4, b_top),
        (b_left + 2, b_top - 4)
    ]
    lh_fill = [
        (b_left + 2, b_top),
        (b_left + 3, b_top),
        (b_left + 2, b_top - 2)
    ]
    # Right horn
    rh_outline = [
        (b_right - 4, b_top),
        (b_right - 1, b_top),
        (b_right - 2, b_top - 4)
    ]
    rh_fill = [
        (b_right - 3, b_top),
        (b_right - 2, b_top),
        (b_right - 2, b_top - 2)
    ]
    
    # Draw horn outlines
    draw.polygon(lh_outline, fill=horn_outline)
    draw.polygon(rh_outline, fill=horn_outline)
    # Draw horn fills
    draw.polygon(lh_fill, fill=horn_color)
    draw.polygon(rh_fill, fill=horn_color)
    
    # 3. Draw Body Base Fill
    draw.ellipse([b_left, b_top, b_right, b_bottom], fill=body_color)
    
    # 4. Draw Shading & Highlights
    # Bottom shading (semi-transparent dark band)
    draw.chord([b_left, b_top + 10, b_right, b_bottom], start=0, end=180, fill=(0, 0, 0, 40))
    # Top highlight
    draw.arc([b_left + 2, b_top + 2, b_right - 2, b_bottom - 2], start=200, end=340, fill=(255, 255, 255, 60))
    
    # 5. Draw Face (Eyes & Mouth)
    eye_w = 4
    eye_h = 5
    
    le_left = b_left + 3
    le_top = b_top + 4
    le_right = le_left + eye_w
    le_bottom = le_top + eye_h
    
    re_left = b_right - 3 - eye_w
    re_top = b_top + 4
    re_right = re_left + eye_w
    re_bottom = re_top + eye_h
    
    if state == "success":
        # Success: happy arch eyes '^ ^' in outline color
        draw.line([(le_left, le_bottom - 1), (le_left + 2, le_top + 1), (le_right, le_bottom - 1)], fill=outline_color, width=1)
        draw.line([(re_left, re_bottom - 1), (re_left + 2, re_top + 1), (re_right, re_bottom - 1)], fill=outline_color, width=1)
        
        # Happy open mouth: polygon triangle pointing down
        m_pts = [
            (b_left + 8, b_top + 10),
            (b_right - 8, b_top + 10),
            (16, b_top + 13)
        ]
        draw.polygon(m_pts, fill=outline_color)
        
        # Success sparkles (yellow single pixels)
        sparkle_color = (241, 196, 15, 255)
        if frame_idx % 2 == 0:
            draw.point((b_left - 3, b_top + 2), fill=sparkle_color)
            draw.point((b_right + 3, b_top + 5), fill=sparkle_color)
        else:
            draw.point((b_left - 2, b_top + 6), fill=sparkle_color)
            draw.point((b_right + 2, b_top + 1), fill=sparkle_color)
            
    elif state == "error":
        # Error: slanted angry eyes / crossed eyes
        # Left eye
        draw.ellipse([le_left - 1, le_top - 1, le_right + 1, le_bottom + 1], fill=outline_color)
        draw.ellipse([le_left, le_top, le_right, le_bottom], fill=(255, 255, 255, 255))
        # Right eye
        draw.ellipse([re_left - 1, re_top - 1, re_right + 1, re_bottom + 1], fill=outline_color)
        draw.ellipse([re_left, re_top, re_right, re_bottom], fill=(255, 255, 255, 255))
        
        # Pupils: crossed X shape
        draw.line([(le_left + 1, le_top + 1), (le_right - 1, le_bottom - 1)], fill=outline_color, width=1)
        draw.line([(le_left + 1, le_bottom - 1), (le_right - 1, le_top + 1)], fill=outline_color, width=1)
        draw.line([(re_left + 1, re_top + 1), (re_right - 1, re_bottom - 1)], fill=outline_color, width=1)
        draw.line([(re_left + 1, re_bottom - 1), (re_right - 1, le_top + 1)], fill=outline_color, width=1)
        
        # Angry eyebrows
        draw.line([(le_left - 1, le_top - 2), (le_right + 1, le_top - 1)], fill=outline_color, width=1)
        draw.line([(re_right + 1, re_top - 2), (re_left - 1, re_top - 1)], fill=outline_color, width=1)
        
        # Open mouth (scream)
        draw.ellipse([14, b_top + 10, 17, b_top + 13], fill=outline_color)
        
    elif state == "typing":
        # Typing: eyes dart left and right
        draw.ellipse([le_left - 1, le_top - 1, le_right + 1, le_bottom + 1], fill=outline_color)
        draw.ellipse([le_left, le_top, le_right, le_bottom], fill=(255, 255, 255, 255))
        draw.ellipse([re_left - 1, re_top - 1, re_right + 1, re_bottom + 1], fill=outline_color)
        draw.ellipse([re_left, re_top, re_right, re_bottom], fill=(255, 255, 255, 255))
        
        pupil_offset = -1 if (frame_idx % 2 == 0) else 1
        draw.rectangle([le_left + 2 + pupil_offset, le_top + 2, le_left + 2 + pupil_offset, le_top + 3], fill=outline_color)
        draw.rectangle([re_left + 2 + pupil_offset, re_top + 2, re_left + 2 + pupil_offset, re_top + 3], fill=outline_color)
        
        # Mouth: simple line
        draw.line([(14, b_top + 10), (17, b_top + 10)], fill=outline_color)
        
        # Keyboard at bottom
        kb_color = (100, 110, 120, 255)
        kb_box = [b_left + 3, b_bottom - 4, b_right - 3, b_bottom - 2]
        draw.rectangle(kb_box, fill=kb_color)
        draw.rectangle([kb_box[0] - 1, kb_box[1] - 1, kb_box[2] + 1, kb_box[3] + 1], outline=outline_color, width=1)
        
        # Typing hands (floating circles) alternating heights
        hand_y_offset = -2 if (frame_idx % 2 == 0) else 1
        lh_x = b_left + 1
        lh_y = b_bottom - 5 + hand_y_offset
        draw.ellipse([lh_x, lh_y, lh_x + 2, lh_y + 2], fill=horn_color)
        draw.ellipse([lh_x, lh_y, lh_x + 2, lh_y + 2], outline=outline_color, width=1)
        
        rh_x = b_right - 3
        rh_y = b_bottom - 5 - hand_y_offset
        draw.ellipse([rh_x, rh_y, rh_x + 2, rh_y + 2], fill=horn_color)
        draw.ellipse([rh_x, rh_y, rh_x + 2, rh_y + 2], outline=outline_color, width=1)
        
    elif state == "thinking":
        # Thinking: eyes look up, gear rotates above head
        draw.ellipse([le_left - 1, le_top - 1, le_right + 1, le_bottom + 1], fill=outline_color)
        draw.ellipse([le_left, le_top, le_right, le_bottom], fill=(255, 255, 255, 255))
        draw.ellipse([re_left - 1, re_top - 1, re_right + 1, re_bottom + 1], fill=outline_color)
        draw.ellipse([re_left, re_top, re_right, re_bottom], fill=(255, 255, 255, 255))
        
        # Pupils look up
        draw.rectangle([le_left + 2, le_top + 1, le_left + 2, le_top + 2], fill=outline_color)
        draw.rectangle([re_left + 2, re_top + 1, re_left + 2, re_top + 2], fill=outline_color)
        
        # Curvy mouth
        draw.point((15, b_top + 10), fill=outline_color)
        draw.point((16, b_top + 11), fill=outline_color)
        draw.point((17, b_top + 10), fill=outline_color)
        
        # Rotating gear centered at (16, 4)
        gear_center = (16, 4)
        gear_color = (189, 195, 199, 255)
        draw.ellipse([gear_center[0] - 2, gear_center[1] - 2, gear_center[0] + 2, gear_center[1] + 2], fill=gear_color)
        draw.ellipse([gear_center[0] - 2, gear_center[1] - 2, gear_center[0] + 2, gear_center[1] + 2], outline=outline_color, width=1)
        
        if frame_idx % 2 == 0:
            draw.point((gear_center[0], gear_center[1] - 3), fill=outline_color)
            draw.point((gear_center[0], gear_center[1] + 3), fill=outline_color)
            draw.point((gear_center[0] - 3, gear_center[1]), fill=outline_color)
            draw.point((gear_center[0] + 3, gear_center[1]), fill=outline_color)
        else:
            draw.point((gear_center[0] - 2, gear_center[1] - 2), fill=outline_color)
            draw.point((gear_center[0] + 2, gear_center[1] - 2), fill=outline_color)
            draw.point((gear_center[0] - 2, gear_center[1] + 2), fill=outline_color)
            draw.point((gear_center[0] + 2, gear_center[1] + 2), fill=outline_color)
            
        draw.point(gear_center, fill=(0, 0, 0, 0)) # transparent hole
        
    else: # idle
        is_blinking = (frame_idx % 4 == 2)
        if is_blinking:
            draw.line([(le_left, le_top + 2), (le_right, le_top + 2)], fill=outline_color, width=1)
            draw.line([(re_left, re_top + 2), (re_right, re_top + 2)], fill=outline_color, width=1)
        else:
            draw.ellipse([le_left - 1, le_top - 1, le_right + 1, le_bottom + 1], fill=outline_color)
            draw.ellipse([le_left, le_top, le_right, le_bottom], fill=(255, 255, 255, 255))
            draw.ellipse([re_left - 1, re_top - 1, re_right + 1, re_bottom + 1], fill=outline_color)
            draw.ellipse([re_left, re_top, re_right, re_bottom], fill=(255, 255, 255, 255))
            draw.rectangle([le_left + 2, le_top + 2, le_left + 2, le_top + 3], fill=outline_color)
            draw.rectangle([re_left + 2, re_top + 2, re_left + 2, re_top + 3], fill=outline_color)
            
        draw.line([(15, b_top + 10), (16, b_top + 10)], fill=outline_color)

    # Upscale cleanly using nearest neighbor resampling
    try:
        resampling_filter = Image.Resampling.NEAREST
    except AttributeError:
        resampling_filter = Image.NEAREST
        
    return img.resize((size, size), resampling_filter)

def generate_all(output_dir="assets", size=128):
    """
    Generates all frames for all states and saves them to output_dir.
    """
    states = {
        "idle": 4,
        "thinking": 4,
        "typing": 4,
        "error": 4,
        "success": 4
    }
    
    os.makedirs(output_dir, exist_ok=True)
    
    for state, num_frames in states.items():
        for i in range(num_frames):
            frame = create_sprite(state, i, size)
            frame_path = os.path.join(output_dir, f"{state}_{i}.png")
            frame.save(frame_path)
            print(f"Generated {frame_path}")

def verify_sprites(output_dir="assets", size=128):
    """
    Verifies that all expected frames exist, are valid PNGs of correct size, and contain transparency.
    """
    states = {
        "idle": 4,
        "thinking": 4,
        "typing": 4,
        "error": 4,
        "success": 4
    }
    
    print("Starting sprite verification...")
    errors = []
    
    for state, num_frames in states.items():
        for i in range(num_frames):
            filename = f"{state}_{i}.png"
            filepath = os.path.join(output_dir, filename)
            
            if not os.path.exists(filepath):
                errors.append(f"Missing file: {filepath}")
                continue
                
            try:
                with Image.open(filepath) as img:
                    if img.format != "PNG":
                        errors.append(f"File {filename} is not a PNG (got {img.format})")
                    if img.size != (size, size):
                        errors.append(f"File {filename} size is {img.size}, expected {(size, size)}")
                    if img.mode != "RGBA":
                        errors.append(f"File {filename} mode is {img.mode}, expected RGBA")
                    
                    # Check for transparency (ensure alpha band has transparent values)
                    alpha = img.getchannel('A')
                    extrema = alpha.getextrema() # (min, max) alpha values
                    if extrema[0] == 255:
                        errors.append(f"File {filename} has no transparent pixels (alpha min is 255)")
            except Exception as e:
                errors.append(f"Failed to open/verify {filename}: {str(e)}")
                
    if errors:
        print("Verification FAILED! Errors found:")
        for err in errors:
            print(f" - {err}")
        return False
        
    print("Verification SUCCESSFUL! All frames verified successfully.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DaemonSprite procedural asset generator.")
    parser.add_argument("--output-dir", default="assets", help="Target directory for generated sprites.")
    parser.add_argument("--size", type=int, default=128, help="Size of output square images (e.g. 128 or 256).")
    parser.add_argument("--palette", default=None, help="Hex color code or predefined palette name.")
    parser.add_argument("--verify", action="store_true", help="Run verification check on existing files instead of generating.")
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_sprites(args.output_dir, args.size)
        sys.exit(0 if success else 1)
    else:
        generate_all(args.output_dir, args.size)
        success = verify_sprites(args.output_dir, args.size)
        sys.exit(0 if success else 1)
