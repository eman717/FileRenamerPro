"""
Build script to create standalone .exe for File Renamer Pro v2
Run this script to generate the executable.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

def build(version: str = "v2"):
    print("=" * 50)
    print(f"  Building File Renamer Pro {version} Executable")
    print("=" * 50)
    print()

    # Change to script directory
    os.chdir(SCRIPT_DIR)

    # Determine which source file to use
    if version == "v2":
        source_file = "file_renamer_pro_v2.py"
    else:
        source_file = "file_renamer_pro.py"

    if not Path(source_file).exists():
        print(f"ERROR: Source file not found: {source_file}")
        return 1

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # Single .exe file
        "--windowed",                         # No console window
        "--name", "FileRenamerPro",           # Output name
        "--icon", "app_icon.ico",             # Custom icon
        "--add-data", "config.json;.",        # Include config file
        "--add-data", "src;src",              # Include src module
        "--clean",                            # Clean cache before building
        "--noconfirm",                        # Overwrite without asking
        "--hidden-import", "src.theme",
        "--hidden-import", "src.config",
        "--hidden-import", "src.job_parser",
        "--hidden-import", "src.timer",
        "--hidden-import", "src.revision",
        "--hidden-import", "src.services",
        "--hidden-import", "src.utils",
        "--hidden-import", "src.widgets",
        source_file
    ]

    print("Running PyInstaller...")
    print(f"Source: {source_file}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  BUILD SUCCESSFUL!")
        print("=" * 50)
        print()
        
        exe_path = SCRIPT_DIR / 'dist' / 'FileRenamerPro.exe'
        print(f"Executable created at:")
        print(f"  {exe_path}")
        print()

        # Copy to USB_Deploy
        usb_deploy = SCRIPT_DIR / 'USB_Deploy'
        usb_deploy.mkdir(exist_ok=True)
        
        dest_exe = usb_deploy / 'FileRenamerPro.exe'
        dest_config = usb_deploy / 'config.json'
        
        try:
            shutil.copy2(exe_path, dest_exe)
            shutil.copy2(SCRIPT_DIR / 'config.json', dest_config)
            print("Copied to USB_Deploy folder:")
            print(f"  {dest_exe}")
            print(f"  {dest_config}")
        except Exception as e:
            print(f"Warning: Could not copy to USB_Deploy: {e}")

        print()
        print("To deploy to USB:")
        print("  1. Copy 'FileRenamerPro.exe' from 'USB_Deploy' folder")
        print("  2. Copy 'config.json' for customization")
        print("  3. The app will create 'time_logs' folder automatically")
        print()
    else:
        print()
        print("BUILD FAILED! Check errors above.")
        return 1

    return 0


if __name__ == "__main__":
    # Parse version argument
    version = "v2"
    if len(sys.argv) > 1:
        if sys.argv[1] in ["v1", "v2"]:
            version = sys.argv[1]
        elif sys.argv[1] == "--help":
            print("Usage: python build_exe.py [v1|v2]")
            print("  v1 - Build original single-file version")
            print("  v2 - Build new modular version (default)")
            sys.exit(0)
    
    sys.exit(build(version))
