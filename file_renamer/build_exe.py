"""
Build script to create standalone .exe for File Renamer Pro
Run this script to generate the executable.
"""

import subprocess
import sys
import os
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

def build():
    print("=" * 50)
    print("  Building File Renamer Pro Executable")
    print("=" * 50)
    print()

    # Change to script directory
    os.chdir(SCRIPT_DIR)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # Single .exe file
        "--windowed",                         # No console window
        "--name", "FileRenamerPro",           # Output name
        "--icon", "app_icon.ico",             # Custom icon
        "--add-data", "config.json;.",        # Include config file
        "--clean",                            # Clean cache before building
        "--noconfirm",                        # Overwrite without asking
        "file_renamer_pro.py"
    ]

    print("Running PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  BUILD SUCCESSFUL!")
        print("=" * 50)
        print()
        print(f"Executable created at:")
        print(f"  {SCRIPT_DIR / 'dist' / 'FileRenamerPro.exe'}")
        print()
        print("To deploy to USB:")
        print("  1. Copy 'FileRenamerPro.exe' from the 'dist' folder")
        print("  2. Copy 'config.json' (for customization)")
        print("  3. The app will create 'time_logs' folder automatically")
        print()
    else:
        print()
        print("BUILD FAILED! Check errors above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(build())
