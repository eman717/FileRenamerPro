# Project Management Tools

Collection of internal tools for ILN workflow management.

**Repository**: https://github.com/eman717/FileRenamerPro

## File Renamer Pro v2.0

A desktop application for standardized artwork file naming and time tracking.

### Location
`file_renamer/`

### Purpose
Renames artwork files to follow the naming convention:
```
<Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>
```

Example: `12345_MUG-11OZ_(BlueDog)_PROOF_1.psd`

### Job Folder Structure
The app expects job folders named: `Job#_CustomerName_Company_SKU x Qty_(PO#)`

Example: `12345_JohnDoe_AcmeCorp_MUG-11OZ x 100_(PO-98765)`

With subfolders:
- `1_TheirPOs` - Customer purchase orders
- `2_OurDocs` - Internal documents
- `3_ProvidedArt` - Customer-provided artwork
- `4_ArtSetups` - Main design files and production output
- `5_VirtualProofs` - Proof files for customer approval

### Features
- **Three Drop Zones**: Main Design (SOURCE), Virtual Proof (PROOF), Production Output (PRINT, CUTFILE, etc.)
- **Auto-Routing**: Files automatically placed in correct subfolder
- **Job Parsing**: Extracts job info from folder name
- **Revision Detection**: Auto-detects next revision number
- **Time Tracking**: Clock in/out with session logging
- **Portable**: Runs from USB, no installation required
- **Undo/Redo**: Full undo/redo support for file renames (Ctrl+Z/Ctrl+Y)
- **Keyboard Shortcuts**: Ctrl+O (browse), Ctrl+R (rename), Ctrl+L (logs), Ctrl+, (settings)
- **Settings GUI**: In-app configuration editor
- **Recent Jobs**: Quick access to recently used job folders
- **Duplicate Handling**: Skip, auto-increment, or overwrite options
- **Status Bar**: Persistent feedback messages
- **Tooltips**: Hover hints on all buttons
- **Cross-Platform**: Works on Windows, macOS, and Linux

### Project Structure
```
file_renamer/
├── src/                        # Modular source code
│   ├── __init__.py
│   ├── theme.py                # Design system & colors
│   ├── config.py               # Configuration management
│   ├── job_parser.py           # Job folder name parsing
│   ├── timer.py                # Time tracking
│   ├── revision.py             # Revision detection
│   ├── services.py             # Rename service & undo manager
│   ├── utils.py                # Utility functions
│   ├── widgets.py              # Custom UI components
│   └── settings_dialog.py      # Settings GUI
├── tests/                      # Unit tests
│   ├── __init__.py
│   ├── test_job_parser.py
│   └── test_utils.py
├── USB_Deploy/                 # Deployment folder
│   ├── FileRenamerPro.exe
│   └── config.json
├── file_renamer_pro.py         # Original v1 application
├── file_renamer_pro_v2.py      # New v2 application (recommended)
├── build_exe.py                # Build script
├── config.json                 # Configuration file
└── app_icon.ico                # Application icon
```

### Dependencies
```
tkinter (built-in)
tkinterdnd2 (optional, for drag-drop support)
Pillow (for icon generation only)
PyInstaller (for building exe)
pytest (for running tests)
```

### Running from Source
```bash
cd file_renamer
python file_renamer_pro_v2.py
```

### Running Tests
```bash
cd file_renamer
python -m pytest tests/ -v
```

### Building Executable
```bash
cd file_renamer
python build_exe.py v2      # Build v2 (default)
python build_exe.py v1      # Build v1 (legacy)
```
Output: `dist/FileRenamerPro.exe` (also copied to `USB_Deploy/`)

### Deployment
1. Copy `FileRenamerPro.exe` from `USB_Deploy/` folder
2. Optionally copy `config.json` for customization
3. App creates `time_logs/` folder automatically for session tracking

### Configuration
Edit via Settings GUI (Ctrl+,) or manually edit `config.json`:
- Product SKUs
- Production output types (PRINT, CUTFILE, SUBLIMATION, etc.)
- Timer warning thresholds
- Duplicate handling preferences
- Job folder base directory
- And more...

### Tech Stack
- Python 3 + Tkinter
- Modular architecture with 9 separate modules
- tkinterdnd2 (optional, for drag-drop support)
- PyInstaller (for building exe)
- pytest (for testing)

### UI Theme
Dark "Creative Studio" aesthetic with coral (#ff6b35) accent color, designed for graphic designers.

Color palette:
- Background: #1a1a1f (deep charcoal)
- Cards: #242429 (dark gray)
- Accent: #ff6b35 (coral)
- Success: #45b764 (green)
- Warning: #ffc857 (amber)
- Text: #ffffff (white)

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+O | Browse for job folder |
| Ctrl+R | Rename & move files |
| Ctrl+L | View time logs |
| Ctrl+Z | Undo last rename |
| Ctrl+Y | Redo last undo |
| Ctrl+, | Open settings |
| Escape | Clear all drop zones |

### Version History
- **v2.0** - Major refactor: modular architecture, undo/redo, settings GUI, keyboard shortcuts, status bar, tooltips, cross-platform support, unit tests
- **v1.0** - Initial release: basic file renaming, time tracking, dark theme UI
