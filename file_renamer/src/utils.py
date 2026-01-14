"""
Utility functions for File Renamer Pro
Cross-platform helpers and filename utilities
"""

import os
import re
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# Characters not allowed in filenames on various systems
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
INVALID_FILENAME_PATTERN = re.compile(INVALID_FILENAME_CHARS)

# Reserved Windows filenames
WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        replacement: Character to replace invalid chars with
        
    Returns:
        Sanitized filename safe for all platforms
    """
    if not filename:
        return ""

    # Remove/replace invalid characters
    sanitized = INVALID_FILENAME_PATTERN.sub(replacement, filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')

    # Check for Windows reserved names
    name_without_ext = sanitized.rsplit('.', 1)[0].upper()
    if name_without_ext in WINDOWS_RESERVED:
        sanitized = f"_{sanitized}"

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"

    # Limit length (255 is common max, but leave room for path)
    max_length = 200
    if len(sanitized) > max_length:
        # Preserve extension
        parts = sanitized.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            sanitized = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            sanitized = sanitized[:max_length]

    return sanitized


def validate_filename(filename: str) -> tuple[bool, str]:
    """
    Validate a filename for use on the filesystem.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is empty"

    if INVALID_FILENAME_PATTERN.search(filename):
        return False, "Filename contains invalid characters"

    name_without_ext = filename.rsplit('.', 1)[0].upper()
    if name_without_ext in WINDOWS_RESERVED:
        return False, f"'{name_without_ext}' is a reserved name on Windows"

    if len(filename) > 255:
        return False, "Filename is too long"

    return True, ""


def open_folder(folder_path: str) -> bool:
    """
    Open a folder in the system file browser (cross-platform).
    
    Args:
        folder_path: Path to folder to open
        
    Returns:
        True if successful, False otherwise
    """
    path = Path(folder_path)
    
    if not path.exists():
        logger.error(f"Folder does not exist: {folder_path}")
        return False

    try:
        if sys.platform == 'win32':
            os.startfile(str(path))
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', str(path)], check=True)
        else:  # Linux and others
            subprocess.run(['xdg-open', str(path)], check=True)
        logger.info(f"Opened folder: {folder_path}")
        return True
    except FileNotFoundError:
        logger.error("File browser command not found")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open folder: {e}")
    except Exception as e:
        logger.error(f"Error opening folder: {e}")
    return False


def open_file(file_path: str) -> bool:
    """
    Open a file with the default application (cross-platform).
    
    Args:
        file_path: Path to file to open
        
    Returns:
        True if successful, False otherwise
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"File does not exist: {file_path}")
        return False

    try:
        if sys.platform == 'win32':
            os.startfile(str(path))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(path)], check=True)
        else:
            subprocess.run(['xdg-open', str(path)], check=True)
        return True
    except Exception as e:
        logger.error(f"Error opening file: {e}")
    return False


def get_platform_font(font_type: str = 'body') -> tuple:
    """
    Get appropriate font for the current platform.
    
    Args:
        font_type: One of 'display', 'body', 'small', 'mono'
        
    Returns:
        Font tuple (family, size, weight)
    """
    if sys.platform == 'darwin':
        fonts = {
            'display': ('SF Pro Display', 10, 'bold'),
            'body': ('SF Pro Text', 9, 'normal'),
            'small': ('SF Pro Text', 8, 'normal'),
            'mono': ('SF Mono', 9, 'normal'),
        }
    elif sys.platform == 'win32':
        fonts = {
            'display': ('Segoe UI', 10, 'bold'),
            'body': ('Segoe UI', 9, 'normal'),
            'small': ('Segoe UI', 8, 'normal'),
            'mono': ('Cascadia Code', 9, 'normal'),
        }
    else:
        fonts = {
            'display': ('Ubuntu', 10, 'bold'),
            'body': ('Ubuntu', 9, 'normal'),
            'small': ('Ubuntu', 8, 'normal'),
            'mono': ('Ubuntu Mono', 9, 'normal'),
        }

    return fonts.get(font_type, fonts['body'])


def ensure_directory(path: Path) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Path to directory
        
    Returns:
        True if directory exists or was created
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Permission denied creating directory: {path}")
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
    return False


def get_file_size_str(size_bytes: int) -> str:
    """Convert bytes to human readable string"""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_unique_path(base_path: Path, format_str: str = "_{n}") -> Path:
    """
    Get a unique path by appending a number if path exists.
    
    Args:
        base_path: Original path
        format_str: Format for number suffix (must contain {n})
        
    Returns:
        Unique path that doesn't exist
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    n = 1
    while True:
        new_name = stem + format_str.format(n=n) + suffix
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        n += 1
        if n > 9999:
            raise ValueError("Could not find unique path after 9999 attempts")


def parse_dropped_files(data: str) -> List[str]:
    """
    Parse dropped file data from drag-and-drop.
    Handles various formats from different platforms.
    
    Args:
        data: Raw drop data string
        
    Returns:
        List of file paths
    """
    files = []
    
    # Handle curly brace format (Windows with spaces)
    if '{' in data:
        # Extract paths in curly braces
        files.extend(re.findall(r'\{([^}]+)\}', data))
        # Remove the braced parts and get remaining
        remaining = re.sub(r'\{[^}]+\}', '', data)
        files.extend(remaining.split())
    else:
        # Simple space/newline separated
        files = data.replace('\n', ' ').split()

    # Clean up and filter
    return [f.strip() for f in files if f.strip() and os.path.exists(f.strip())]
