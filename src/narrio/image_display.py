"""Image display utilities for kitty terminal and fallback mechanisms."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def is_kitty_terminal() -> bool:
    """
    Detect if the current terminal is kitty.

    Checks:
    1. KITTY_LISTEN_ON environment variable
    2. TERM environment variable equals 'xterm-kitty'
    """
    # Check for KITTY_LISTEN_ON
    if os.getenv("KITTY_LISTEN_ON"):
        return True

    # Check for TERM=xterm-kitty
    if os.getenv("TERM") == "xterm-kitty":
        return True

    return False


def is_kitten_available() -> bool:
    """Check if the kitten command is available."""
    try:
        subprocess.run(
            ["kitten", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_pil_available() -> bool:
    """Check if PIL (Pillow) is installed."""
    try:
        import PIL
        return True
    except ImportError:
        return False


def display_image_with_kitten(image_path: str | Path) -> int:
    """
    Display an image using kitten icat.

    Args:
        image_path: Path to the image file

    Returns:
        0 on success, non-zero on failure
    """
    try:
        subprocess.run(
            [
                "kitten",
                "icat",
                "--clear",
                "--transfer-mode=file",
                str(image_path),
            ],
            check=True,
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to display image with kitten icat: {e}")
        return 1
    except FileNotFoundError:
        print("Error: kitten command not found")
        return 1


def display_image_with_pil(image_path: str | Path) -> int:
    """
    Display an image using Python PIL (opens in system default viewer).

    Args:
        image_path: Path to the image file

    Returns:
        0 on success, non-zero on failure
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        img.show()
        return 0
    except ImportError:
        print("Error: PIL (Pillow) is not installed")
        print("Install with: pip install Pillow")
        return 1
    except Exception as e:
        print(f"Error: Failed to display image with PIL: {e}")
        return 1


def display_image(image_path: str | Path, force_pil: bool = False) -> int:
    """
    Display an image using the best available method.

    Priority:
    1. kitten icat (if kitty terminal and not force_pil)
    2. PIL fallback
    3. Print path only

    Args:
        image_path: Path to the image file
        force_pil: Force using PIL even if kitty is available

    Returns:
        0 on success, non-zero on failure
    """
    image_path = Path(image_path)

    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        return 1

    # Try kitten icat if in kitty terminal and not forcing PIL
    if not force_pil and is_kitty_terminal():
        if is_kitten_available():
            print(f"Displaying image with kitten icat: {image_path}")
            return display_image_with_kitten(image_path)
        else:
            print("Warning: kitty detected but kitten command not available, falling back to PIL")

    # Try PIL fallback
    if is_pil_available():
        print(f"Displaying image with PIL: {image_path}")
        return display_image_with_pil(image_path)

    # No display method available, just print the path
    print(f"Image saved at: {image_path}")
    print("Note: Install Pillow for automatic image display (pip install Pillow)")
    return 0
