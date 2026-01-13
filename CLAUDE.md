# Project Management Tools

Collection of internal tools for ILN workflow management.

## File Renamer Pro

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

### Key Files
- `file_renamer_pro.py` - Main application (dark theme UI)
- `config.json` - Customizable SKUs, production types, settings
- `build_exe.py` - Build script for standalone .exe
- `create_icon.py` - Generates app icon

### Building
```bash
cd file_renamer
python build_exe.py
```
Output: `dist/FileRenamerPro.exe`

### Tech Stack
- Python 3 + Tkinter
- tkinterdnd2 (optional, for drag-drop support)
- PyInstaller (for building exe)

### UI Theme
Dark "Creative Studio" aesthetic with coral (#ff6b35) accent color, designed for graphic designers.
