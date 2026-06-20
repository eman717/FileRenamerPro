"""
Job Art Naming Helper v2 - Artwork job & naming tool with time tracking
(formerly "File Renamer Pro")
Refactored with modular architecture, undo/redo, and improved UX

Naming Convention: <Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>

Job Folder Structure:
- Main folder: Job#_CustomerName_Company_SKU x Qty_(PO#)
  - 1_TheirPOs
  - 2_OurDocs
  - 3_ProvidedArt
  - 4_ArtSetups      <- MainDesign & ProductionOutput files go here
  - 5_VirtualProofs  <- Proof files go here
"""

import os
import re
import sys
import shutil
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from typing import Optional

# Setup logging. Also write to a log file next to the app (exe when frozen,
# otherwise this script) so errors are visible even when run without a console.
if getattr(sys, "frozen", False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(_app_dir, "file_renamer.log")

_handlers = [logging.StreamHandler()]
try:
    _handlers.append(logging.FileHandler(_log_file, encoding="utf-8"))
except OSError:
    pass  # read-only location (e.g. some USB setups) — console logging only

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

# Add src to path for imports
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from src.theme import Theme
from src.config import Config, load_config, save_config
from src.job_parser import JobFolderParser
from src.timer import TimerManager
from src.revision import RevisionDetector
from src.services import RenameService, UndoManager
from src.utils import open_folder, open_file, sanitize_filename, ensure_directory
from src.widgets import (
    StyledButton, SectionCard, DropZone, StyledEntry, 
    StatusBar, ScrollableFrame, Tooltip
)
from src.settings_dialog import SettingsDialog

# Try to import drag-drop support
try:
    from tkinterdnd2 import TkinterDnD
    HAS_DND = True
    DND_INSTALL_ERROR = None
except ImportError as e:
    HAS_DND = False
    DND_INSTALL_ERROR = str(e)


def check_and_install_dnd():
    """Check for tkinterdnd2 and offer to install it"""
    if HAS_DND:
        return True
    
    # Create a simple dialog to ask user
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    result = messagebox.askyesno(
        "Drag & Drop Support",
        "The tkinterdnd2 package is not installed.\n\n"
        "This package enables drag & drop functionality, which makes "
        "adding files much easier.\n\n"
        "Would you like to install it now?\n\n"
        "(Requires internet connection. App will restart after installation.)",
        icon='question'
    )
    
    if result:
        root.destroy()
        return install_tkinterdnd2()
    
    # User declined - show info about manual install
    messagebox.showinfo(
        "Continuing Without Drag & Drop",
        "You can still use the app by clicking the '+ MAIN', '+ PROOF', "
        "and '+ PROD' buttons to add files.\n\n"
        "To install drag & drop support later, run:\n"
        "pip install tkinterdnd2"
    )
    root.destroy()
    return False


def install_tkinterdnd2():
    """Attempt to install tkinterdnd2 using pip"""
    import subprocess
    
    # Show progress window
    progress_root = tk.Tk()
    progress_root.title("Installing...")
    progress_root.geometry("350x100")
    progress_root.resizable(False, False)
    
    # Center on screen
    progress_root.update_idletasks()
    x = (progress_root.winfo_screenwidth() - 350) // 2
    y = (progress_root.winfo_screenheight() - 100) // 2
    progress_root.geometry(f"+{x}+{y}")
    
    label = tk.Label(progress_root, text="Installing tkinterdnd2...\nPlease wait...", 
                    font=("Segoe UI", 11), pady=20)
    label.pack(expand=True)
    progress_root.update()
    
    try:
        # Run pip install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "tkinterdnd2"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        progress_root.destroy()
        
        if result.returncode == 0:
            messagebox.showinfo(
                "Installation Successful",
                "tkinterdnd2 has been installed successfully!\n\n"
                "The application will now restart to enable drag & drop."
            )
            # Restart the application
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True
        else:
            messagebox.showerror(
                "Installation Failed",
                f"Failed to install tkinterdnd2.\n\n"
                f"Error: {result.stderr}\n\n"
                "You can try installing manually by running:\n"
                "pip install tkinterdnd2"
            )
            return False
            
    except subprocess.TimeoutExpired:
        progress_root.destroy()
        messagebox.showerror(
            "Installation Timeout",
            "Installation timed out. Please check your internet connection "
            "and try installing manually:\n\npip install tkinterdnd2"
        )
        return False
    except Exception as e:
        progress_root.destroy()
        messagebox.showerror(
            "Installation Error",
            f"An error occurred during installation:\n{e}\n\n"
            "Please try installing manually:\npip install tkinterdnd2"
        )
        return False

# Configuration paths. Read/write config.json next to the app so settings
# (incl. the Recent list) persist. In a frozen --onefile build, SCRIPT_DIR is a
# temp extraction dir, so use the exe's directory and seed it from the bundled
# default config on first run.
if getattr(sys, "frozen", False):
    CONFIG_FILE = Path(_app_dir) / "config.json"
    _bundled_config = Path(getattr(sys, "_MEIPASS", _app_dir)) / "config.json"
    if not CONFIG_FILE.exists() and _bundled_config.exists():
        try:
            shutil.copy2(_bundled_config, CONFIG_FILE)
        except OSError:
            logger.warning("Could not seed config.json next to the exe")
else:
    CONFIG_FILE = SCRIPT_DIR / "config.json"

# Subfolder names
SUBFOLDER_ART_SETUPS = "4_ArtSetups"
SUBFOLDER_PROOFS = "5_VirtualProofs"

# The five standard subfolders expected inside every job folder
STANDARD_SUBFOLDERS = [
    "1_TheirPOs",
    "2_OurDocs",
    "3_ProvidedArt",
    SUBFOLDER_ART_SETUPS,
    SUBFOLDER_PROOFS,
]


class JobArtNamingHelper:
    """Main application class for Job Art Naming Helper"""

    def __init__(self, root):
        self.root = root
        self.root.title("Job Art Naming Helper")
        # Narrow, tall default (≈1/4–1/3 of a 1920-wide screen); fully resizable
        self.root.geometry("600x860")
        self.root.minsize(440, 560)
        self.root.resizable(True, True)
        self.root.configure(bg=Theme.BG_PRIMARY)

        # Load configuration
        self.config = load_config(CONFIG_FILE)

        # Initialize managers
        log_dir = SCRIPT_DIR / self.config.log_directory
        self.timer = TimerManager(log_dir)
        self.revision_detector = RevisionDetector(self.config.revisions)
        self.undo_manager = UndoManager()
        self.rename_service = RenameService(self.undo_manager)

        # State
        self.job_folder_path: Optional[str] = None
        self.job_info = {}
        self.files_renamed_this_session = 0
        self.auto_revision_enabled = tk.BooleanVar(value=True)
        self._last_folder_sig = None  # for live folder-contents refresh

        # Setup UI
        self._setup_styles()
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        # Watch the job folder so the file lists reflect on-disk changes live
        self._poll_folder_contents()
        self._start_timer_update()

        # Set icon
        self._set_icon()

        logger.info("Job Art Naming Helper initialized")

    def _set_icon(self):
        """Set application icon"""
        try:
            icon_path = SCRIPT_DIR / "app_icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception as e:
            logger.debug(f"Could not set icon: {e}")

    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dark.TCombobox", 
                       fieldbackground=Theme.BG_TERTIARY, 
                       background=Theme.BG_TERTIARY,
                       foreground=Theme.TEXT_PRIMARY, 
                       arrowcolor=Theme.TEXT_SECONDARY, 
                       borderwidth=0, 
                       padding=8)
        style.map("Dark.TCombobox", 
                 fieldbackground=[("readonly", Theme.BG_TERTIARY)],
                 foreground=[("disabled", Theme.TEXT_TERTIARY)])
        style.configure("Dark.TCheckbutton", 
                       background=Theme.BG_SECONDARY, 
                       foreground=Theme.TEXT_SECONDARY,
                       font=Theme.FONT_SMALL)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<Control-o>", lambda e: self.browse_job_folder())
        self.root.bind("<Control-r>", lambda e: self.rename_files())
        self.root.bind("<Control-l>", lambda e: self.view_time_logs())
        self.root.bind("<Control-z>", lambda e: self.undo_rename())
        self.root.bind("<Control-y>", lambda e: self.redo_rename())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())
        self.root.bind("<Escape>", lambda e: self.clear_all())
        logger.debug("Keyboard shortcuts configured")

    def _setup_ui(self):
        """Setup the main UI"""
        # Main scrollable container
        self.scroll_frame = ScrollableFrame(self.root, bg=Theme.BG_PRIMARY)
        self.scroll_frame.pack(fill="both", expand=True, padx=Theme.PAD_MD, pady=Theme.PAD_MD)

        main_frame = self.scroll_frame.scrollable_frame
        main_frame.columnconfigure(0, weight=1)

        # Create sections
        self._create_header(main_frame)
        self._create_timer_section(main_frame)
        self._create_job_section(main_frame)
        self._create_folder_contents(main_frame)
        self._create_drop_zones(main_frame)
        self._create_action_bar(main_frame)

        # Status bar at bottom (outside scroll)
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill="x", side="bottom")

    def _create_header(self, parent):
        """Create header section"""
        header = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        header.grid(row=0, column=0, sticky="ew", pady=(0, Theme.PAD_MD))

        title_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        title_frame.pack(side="left")

        tk.Label(title_frame, text="JOB ART NAMING", font=Theme.FONT_TITLE,
                fg=Theme.TEXT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")
        tk.Label(title_frame, text=" HELPER", font=Theme.FONT_TITLE,
                fg=Theme.ACCENT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")

        tk.Label(header, text="Artwork job & naming tool v2.0", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_PRIMARY).pack(side="left", padx=(Theme.PAD_MD, 0), pady=(8, 0))

        # Undo/Redo and Settings buttons
        btn_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        btn_frame.pack(side="right")

        self.settings_btn = StyledButton(btn_frame, text="SETTINGS", command=self.open_settings,
                                        variant="secondary", width=80, height=28)
        self.settings_btn.pack(side="left", padx=(0, Theme.PAD_SM))
        self.settings_btn.set_tooltip("Open settings (Ctrl+,)")

        self.undo_btn = StyledButton(btn_frame, text="UNDO", command=self.undo_rename,
                                     variant="secondary", width=70, height=28)
        self.undo_btn.pack(side="left", padx=(0, Theme.PAD_XS))
        self.undo_btn.set_enabled(False)
        self.undo_btn.set_tooltip("Undo last rename (Ctrl+Z)")

        self.redo_btn = StyledButton(btn_frame, text="REDO", command=self.redo_rename,
                                     variant="secondary", width=70, height=28)
        self.redo_btn.pack(side="left")
        self.redo_btn.set_enabled(False)
        self.redo_btn.set_tooltip("Redo last undo (Ctrl+Y)")

    def _create_timer_section(self, parent):
        """Create timer section"""
        card = SectionCard(parent, title="Session Timer")
        card.grid(row=1, column=0, sticky="ew", pady=(0, Theme.PAD_MD))

        content = card.content
        timer_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        timer_row.pack(fill="x")

        self.timer_display = tk.Label(timer_row, text="00:00:00", font=Theme.FONT_MONO_LARGE,
                                      fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY)
        self.timer_display.pack(side="left")

        right_frame = tk.Frame(timer_row, bg=Theme.BG_SECONDARY)
        right_frame.pack(side="right")

        self.timer_status = tk.Label(right_frame, text="Select a job folder to begin",
                                     font=Theme.FONT_BODY, fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY)
        self.timer_status.pack(anchor="e")

        self.session_stats = tk.Label(right_frame, text="Files renamed: 0",
                                      font=Theme.FONT_SMALL, fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY)
        self.session_stats.pack(anchor="e", pady=(Theme.PAD_XS, Theme.PAD_SM))

        btn_frame = tk.Frame(right_frame, bg=Theme.BG_SECONDARY)
        btn_frame.pack(anchor="e")

        self.clock_in_btn = StyledButton(btn_frame, text="CLOCK IN", command=self.handle_clock_in,
                                         variant="success", width=100, height=32)
        self.clock_in_btn.pack(side="left", padx=(0, Theme.PAD_SM))

        self.clock_out_btn = StyledButton(btn_frame, text="CLOCK OUT", command=self.handle_clock_out,
                                          variant="danger", width=100, height=32)
        self.clock_out_btn.pack(side="left")
        self.clock_out_btn.set_enabled(False)

    def _create_job_section(self, parent):
        """Create job details section"""
        card = SectionCard(parent, title="Job Details")
        card.grid(row=2, column=0, sticky="ew", pady=(0, Theme.PAD_MD))

        content = card.content

        # Job Folder Row
        folder_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        folder_row.pack(fill="x", pady=(0, Theme.PAD_SM))

        label_row = tk.Frame(folder_row, bg=Theme.BG_SECONDARY)
        label_row.pack(fill="x")
        
        tk.Label(label_row, text="JOB FOLDER", font=Theme.FONT_SECTION,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(side="left")

        # Recent folders — opens a readable picker centered over the app
        self.recent_btn = StyledButton(label_row, text="RECENT",
                                       command=self.show_recent_folders,
                                       variant="secondary", width=80, height=26)
        self.recent_btn.pack(side="right")
        self.recent_btn.set_tooltip("Open a recently used job folder")

        input_row = tk.Frame(folder_row, bg=Theme.BG_SECONDARY)
        input_row.pack(fill="x", pady=(Theme.PAD_XS, 0))

        self.job_folder_display = StyledEntry(input_row, placeholder="Select main job folder... (Ctrl+O)")
        self.job_folder_display.pack(side="left", fill="x", expand=True, ipady=6)
        self.job_folder_display.config(state="readonly")
        # The path is selectable/copyable even while readonly. Add a right-click
        # "Copy" menu and Ctrl+A select-all so it's obviously copy/pastable.
        self._folder_menu = tk.Menu(self.job_folder_display, tearoff=0)
        self._folder_menu.add_command(label="Copy full path",
                                      command=self._copy_job_folder_path)
        self.job_folder_display.bind("<Button-3>", self._show_folder_menu)
        self.job_folder_display.bind(
            "<Control-a>",
            lambda e: (self.job_folder_display.select_range(0, tk.END),
                       self.job_folder_display.icursor(tk.END), "break")[-1])

        browse_btn = StyledButton(input_row, text="BROWSE", command=self.browse_job_folder,
                                  variant="secondary", width=90, height=34)
        browse_btn.pack(side="right", padx=(Theme.PAD_SM, 0))
        browse_btn.set_tooltip("Browse for job folder (Ctrl+O)")

        # Loaded-job confirmation, shown right below the folder address field
        # (previously only appeared in the status bar at the bottom of the window)
        self.job_loaded_label = tk.Label(folder_row, text="", anchor="w",
                                         font=Theme.FONT_SMALL, fg=Theme.ACCENT_SUCCESS,
                                         bg=Theme.BG_SECONDARY)
        self.job_loaded_label.pack(fill="x", pady=(Theme.PAD_XS, 0))

        # Parsed info display
        self.job_info_frame = tk.Frame(content, bg=Theme.BG_SECONDARY)
        self.job_info_frame.pack(fill="x", pady=(Theme.PAD_SM, 0))

        # Info grid
        info_grid = tk.Frame(self.job_info_frame, bg=Theme.BG_SECONDARY)
        info_grid.pack(fill="x")

        # Row 1: Job#, Customer, Company
        row1 = tk.Frame(info_grid, bg=Theme.BG_SECONDARY)
        row1.pack(fill="x", pady=(0, Theme.PAD_SM))

        self.info_job, self.info_job_src = self._create_info_field(row1, "JOB #", "-")
        self.info_customer, self.info_customer_src = self._create_info_field(row1, "CUSTOMER", "-")
        self.info_company, self.info_company_src = self._create_info_field(row1, "COMPANY", "-")

        # Row 2: SKU, Qty, PO#
        row2 = tk.Frame(info_grid, bg=Theme.BG_SECONDARY)
        row2.pack(fill="x", pady=(0, Theme.PAD_SM))

        self.info_sku, self.info_sku_src = self._create_info_field(row2, "SKU", "-")
        self.info_qty, self.info_qty_src = self._create_info_field(row2, "QTY", "-")
        self.info_po, self.info_po_src = self._create_info_field(row2, "PO #", "-")

        # Row 3: Date (from the date-based job number, or folder created date)
        row3 = tk.Frame(info_grid, bg=Theme.BG_SECONDARY)
        row3.pack(fill="x")

        self.info_date, self.info_date_src = self._create_info_field(row3, "DATE", "-")
        # Empty spacers keep the 3-column alignment with the rows above
        self._create_info_field(row3, "", "")
        self._create_info_field(row3, "", "")

        # Divider
        tk.Frame(content, bg=Theme.BORDER_SUBTLE, height=1).pack(fill="x", pady=Theme.PAD_MD)

        # Artwork Reference
        ref_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        ref_row.pack(fill="x")

        tk.Label(ref_row, text="ARTWORK REFERENCE", font=Theme.FONT_SECTION,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        self.artwork_ref = StyledEntry(ref_row, placeholder="Brief description (e.g., BlueDog, SunsetBeach)")
        self.artwork_ref.pack(fill="x", pady=(Theme.PAD_XS, 0), ipady=6)
        self.artwork_ref.bind('<KeyRelease>', lambda e: self.update_previews())

        # Revision row
        rev_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        rev_row.pack(fill="x", pady=(Theme.PAD_SM, 0))

        tk.Label(rev_row, text="REVISION", font=Theme.FONT_SECTION,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(side="left")

        self.revision = ttk.Combobox(rev_row, values=self.config.revisions, width=8,
                                     state="readonly", style="Dark.TCombobox")
        self.revision.pack(side="left", padx=(Theme.PAD_SM, 0), ipady=2)
        self.revision.current(0)
        self.revision.bind("<<ComboboxSelected>>", lambda e: self.update_previews())

        self.auto_rev_check = ttk.Checkbutton(rev_row, text="Auto-detect", variable=self.auto_revision_enabled,
                                              command=self.detect_revisions, style="Dark.TCheckbutton")
        self.auto_rev_check.pack(side="left", padx=(Theme.PAD_SM, 0))

        self.existing_rev_label = tk.Label(rev_row, text="", font=Theme.FONT_SMALL,
                                           fg=Theme.ACCENT_SECONDARY, bg=Theme.BG_SECONDARY)
        self.existing_rev_label.pack(side="left", padx=(Theme.PAD_MD, 0))

    def _create_info_field(self, parent, label: str, value: str):
        """Create a labeled info field with a small data-source caption below it.

        Returns (value_label, source_label).
        """
        frame = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        frame.pack(side="left", fill="x", expand=True, padx=(0, Theme.PAD_MD))

        tk.Label(frame, text=label, font=("Segoe UI", 8), fg=Theme.TEXT_TERTIARY,
                bg=Theme.BG_SECONDARY).pack(anchor="w")

        value_label = tk.Label(frame, text=value, font=("Segoe UI Semibold", 11),
                               fg=Theme.TEXT_PRIMARY, bg=Theme.BG_SECONDARY)
        value_label.pack(anchor="w")

        source_label = tk.Label(frame, text="", font=Theme.FONT_SMALL,
                                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY)
        source_label.pack(anchor="w")

        return value_label, source_label

    def _create_folder_contents(self, parent):
        """Create the job folder contents section: standard-folder status with a
        create button, and clickable file lists for the two working folders."""
        card = SectionCard(parent, title="Job Folder Contents")
        card.grid(row=3, column=0, sticky="ew", pady=(0, Theme.PAD_MD))
        content = card.content

        # Standard-folders status row + create button
        status_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        status_row.pack(fill="x")

        tk.Label(status_row, text="STANDARD FOLDERS", font=Theme.FONT_SECTION,
                 fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(side="left")

        self.create_folders_btn = StyledButton(
            status_row, text="CREATE FOLDERS", command=self.create_standard_folders,
            variant="secondary", width=140, height=30)
        self.create_folders_btn.pack(side="right")
        self.create_folders_btn.set_tooltip("Create any missing standard subfolders")
        self.create_folders_btn.set_enabled(False)

        self.folders_status_label = tk.Label(
            content, text="Select a job folder to see its contents.",
            font=Theme.FONT_SMALL, fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY,
            anchor="w", justify="left")
        self.folders_status_label.pack(fill="x", pady=(Theme.PAD_XS, Theme.PAD_SM))

        # Clickable file lists for the two working folders
        lists_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        lists_row.pack(fill="both", expand=True)

        self.artsetups_listbox = self._create_file_list(
            lists_row, f"{SUBFOLDER_ART_SETUPS}  (double-click to open)")
        self.proofs_listbox = self._create_file_list(
            lists_row, f"{SUBFOLDER_PROOFS}  (double-click to open)")

    def _create_file_list(self, parent, title: str):
        """Create a titled, clickable file listbox. Returns the Listbox."""
        frame = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        frame.pack(side="left", fill="both", expand=True, padx=(0, Theme.PAD_SM))

        tk.Label(frame, text=title, font=("Segoe UI", 8), fg=Theme.TEXT_TERTIARY,
                 bg=Theme.BG_SECONDARY).pack(anchor="w")

        listbox = tk.Listbox(
            frame, height=6, bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
            selectbackground=Theme.ACCENT_PRIMARY, selectforeground=Theme.TEXT_PRIMARY,
            relief="flat", highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE,
            highlightcolor=Theme.BORDER_FOCUS, activestyle="none", font=Theme.FONT_SMALL)
        listbox.pack(fill="both", expand=True, pady=(Theme.PAD_XS, 0))
        listbox.bind("<Double-Button-1>", self._on_file_list_open)
        listbox._file_paths = []  # parallel list of full paths (None = placeholder)
        return listbox

    def _create_drop_zones(self, parent):
        """Create the three drop zones"""
        card = SectionCard(parent, title="Files to Rename")
        card.grid(row=4, column=0, sticky="nsew", pady=(0, Theme.PAD_MD))

        content = card.content
        content.pack_configure(fill="both", expand=True)

        # Instruction label
        tk.Label(content, text="Drop files into the appropriate zone. They will be renamed and placed in the correct subfolder.",
                font=Theme.FONT_SMALL, fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w", pady=(0, Theme.PAD_SM))

        # Drop zones container
        zones_frame = tk.Frame(content, bg=Theme.BG_SECONDARY)
        zones_frame.pack(fill="both", expand=True)

        zones_frame.columnconfigure(0, weight=1)
        zones_frame.columnconfigure(1, weight=1)
        zones_frame.columnconfigure(2, weight=1)
        zones_frame.rowconfigure(0, weight=1)

        # Main Design Zone
        self.drop_main = DropZone(zones_frame, "Main Design", "-> 4_ArtSetups (SOURCE)",
                                  Theme.DROP_MAIN_DESIGN, icon_text="*")
        self.drop_main.grid(row=0, column=0, sticky="nsew", padx=(0, Theme.PAD_SM), pady=(0, Theme.PAD_SM))
        self.drop_main.on_files_changed = self.update_previews

        # Virtual Proof Zone
        self.drop_proof = DropZone(zones_frame, "Virtual Proof", "-> 5_VirtualProofs (PROOF)",
                                   Theme.DROP_VIRTUAL_PROOF, icon_text="@")
        self.drop_proof.grid(row=0, column=1, sticky="nsew", padx=(0, Theme.PAD_SM), pady=(0, Theme.PAD_SM))
        self.drop_proof.on_files_changed = self.update_previews

        # Production Output Zone
        self.drop_production = DropZone(zones_frame, "Production Output", "-> 4_ArtSetups",
                                        Theme.DROP_PRODUCTION, icon_text="#")
        self.drop_production.grid(row=0, column=2, sticky="nsew", pady=(0, Theme.PAD_SM))
        self.drop_production.on_files_changed = self.update_previews

        # Production type selector
        prod_type_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        prod_type_row.pack(fill="x", pady=(0, Theme.PAD_SM))

        tk.Label(prod_type_row, text="Production Type:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY).pack(side="left")

        self.production_type = ttk.Combobox(prod_type_row, values=self.config.production_types,
                                            width=15, state="readonly", style="Dark.TCombobox")
        self.production_type.pack(side="left", padx=(Theme.PAD_SM, 0), ipady=2)
        self.production_type.current(0)
        self.production_type.bind("<<ComboboxSelected>>", lambda e: self.update_previews())

        # Duplicate handling
        tk.Label(prod_type_row, text="Duplicates:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY).pack(side="left", padx=(Theme.PAD_MD, 0))

        self.duplicate_mode = ttk.Combobox(prod_type_row, values=["Skip", "Auto-increment", "Overwrite"],
                                           width=12, state="readonly", style="Dark.TCombobox")
        self.duplicate_mode.pack(side="left", padx=(Theme.PAD_SM, 0), ipady=2)
        self.duplicate_mode.current(0)

        # Add files buttons
        btn_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        btn_row.pack(fill="x", pady=(Theme.PAD_SM, 0))

        StyledButton(btn_row, text="+ MAIN", command=self.drop_main.add_files_dialog,
                    variant="secondary", width=80, height=28).pack(side="left", padx=(0, Theme.PAD_SM))
        StyledButton(btn_row, text="+ PROOF", command=self.drop_proof.add_files_dialog,
                    variant="secondary", width=80, height=28).pack(side="left", padx=(0, Theme.PAD_SM))
        StyledButton(btn_row, text="+ PROD", command=self.drop_production.add_files_dialog,
                    variant="secondary", width=80, height=28).pack(side="left")

        dnd_text = "Drag & drop enabled" if HAS_DND else "Install tkinterdnd2 for drag & drop"
        dnd_color = Theme.ACCENT_SUCCESS if HAS_DND else Theme.ACCENT_WARNING
        tk.Label(btn_row, text=dnd_text, font=Theme.FONT_SMALL,
                fg=dnd_color, bg=Theme.BG_SECONDARY).pack(side="right")

        # Preview section
        tk.Frame(content, bg=Theme.BORDER_SUBTLE, height=1).pack(fill="x", pady=Theme.PAD_MD)

        tk.Label(content, text="PREVIEW", font=Theme.FONT_SECTION,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        preview_frame = tk.Frame(content, bg=Theme.BG_TERTIARY)
        preview_frame.pack(fill="x", pady=(Theme.PAD_XS, 0))

        self.preview_listbox = tk.Listbox(preview_frame, bg=Theme.BG_TERTIARY, fg=Theme.ACCENT_SECONDARY,
                                          highlightthickness=0, borderwidth=0, font=("Cascadia Code", 9), height=5)
        self.preview_listbox.pack(fill="both", expand=True, padx=Theme.PAD_SM, pady=Theme.PAD_SM)

    def _create_action_bar(self, parent):
        """Create action bar"""
        action_bar = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        action_bar.grid(row=5, column=0, sticky="ew", pady=(0, Theme.PAD_SM))

        left_frame = tk.Frame(action_bar, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left")

        logs_btn = StyledButton(left_frame, text="VIEW LOGS", command=self.view_time_logs,
                               variant="secondary", width=100, height=38)
        logs_btn.pack(side="left", padx=(0, Theme.PAD_SM))
        logs_btn.set_tooltip("Open time logs folder (Ctrl+L)")

        clear_btn = StyledButton(left_frame, text="CLEAR ALL", command=self.clear_all,
                                variant="secondary", width=100, height=38)
        clear_btn.pack(side="left")
        clear_btn.set_tooltip("Clear all drop zones (Escape)")

        self.rename_btn = StyledButton(action_bar, text="RENAME & MOVE FILES",
                                       command=self.rename_files, variant="primary", width=180, height=44)
        self.rename_btn.pack(side="right")
        self.rename_btn.set_tooltip("Rename and move all files (Ctrl+R)")

    # =========================================================================
    # BUSINESS LOGIC
    # =========================================================================

    def browse_job_folder(self):
        """Open folder browser dialog"""
        base_dir = self.config.job_folder_settings.base_directory
        if not base_dir or not os.path.isdir(base_dir):
            base_dir = None
        folder = filedialog.askdirectory(title="Select Main Job Folder", initialdir=base_dir)
        if folder:
            self._load_job_folder_safely(folder)

    def show_recent_folders(self):
        """Open a centered popup listing recent job folders, each shown by its
        readable folder name plus full path (the old combobox truncated them)."""
        recents = list(self.config.job_folder_settings.recent_folders or [])
        if not recents:
            self.status_bar.set_message("No recent folders yet", "info")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Recent Job Folders")
        dlg.configure(bg=Theme.BG_SECONDARY)
        dlg.transient(self.root)

        # Center over the app window
        w, h = 600, 420
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + max((self.root.winfo_width() - w) // 2, 0)
        y = self.root.winfo_rooty() + max((self.root.winfo_height() - h) // 3, 0)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.minsize(360, 240)

        tk.Label(dlg, text="Recent Job Folders", font=Theme.FONT_DISPLAY,
                 fg=Theme.TEXT_PRIMARY, bg=Theme.BG_SECONDARY, anchor="w").pack(
                     fill="x", padx=Theme.PAD_MD, pady=(Theme.PAD_MD, Theme.PAD_SM))

        scroller = ScrollableFrame(dlg, bg=Theme.BG_SECONDARY)
        scroller.pack(fill="both", expand=True, padx=Theme.PAD_MD)
        listframe = scroller.scrollable_frame

        def choose(path):
            if not os.path.isdir(path):
                self.status_bar.set_message("That folder no longer exists", "error")
                return
            dlg.destroy()
            self._load_job_folder_safely(path)

        for path in recents:
            exists = os.path.isdir(path)
            row = tk.Frame(listframe, bg=Theme.BG_TERTIARY,
                           cursor="hand2" if exists else "arrow")
            row.pack(fill="x", pady=2)
            name = os.path.basename(path.rstrip("/\\")) or path
            title = tk.Label(row, text=name + ("" if exists else "   (missing)"),
                             font=("Segoe UI Semibold", 10),
                             fg=Theme.TEXT_PRIMARY if exists else Theme.ACCENT_DANGER,
                             bg=Theme.BG_TERTIARY, anchor="w", justify="left")
            title.pack(fill="x", padx=Theme.PAD_SM, pady=(Theme.PAD_SM, 0))
            sub = tk.Label(row, text=os.path.normpath(path), font=Theme.FONT_SMALL,
                           fg=Theme.TEXT_TERTIARY, bg=Theme.BG_TERTIARY, anchor="w",
                           justify="left", wraplength=w - 60)
            sub.pack(fill="x", padx=Theme.PAD_SM, pady=(0, Theme.PAD_SM))

            widgets = [row, title, sub]
            for wdg in widgets:
                wdg.bind("<Button-1>", lambda e, p=path: choose(p))
                if exists:
                    wdg.bind("<Enter>", lambda e, ws=widgets:
                             [x.config(bg=Theme.BG_ELEVATED) for x in ws])
                    wdg.bind("<Leave>", lambda e, ws=widgets:
                             [x.config(bg=Theme.BG_TERTIARY) for x in ws])

        btn_row = tk.Frame(dlg, bg=Theme.BG_SECONDARY)
        btn_row.pack(fill="x", padx=Theme.PAD_MD, pady=Theme.PAD_MD)
        StyledButton(btn_row, text="CLOSE", command=dlg.destroy,
                     variant="secondary", width=90, height=30).pack(side="right")

        dlg.grab_set()

    def _show_folder_menu(self, event):
        """Show the right-click Copy menu for the job folder path."""
        if not self.job_folder_display.get():
            return
        try:
            self._folder_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._folder_menu.grab_release()

    def _copy_job_folder_path(self):
        """Copy the full job folder path to the clipboard."""
        path = self.job_folder_display.get()
        if not path:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.status_bar.set_message("Copied folder path to clipboard", "info")

    def _load_job_folder_safely(self, folder: str):
        """Load a job folder, surfacing (and logging) any failure."""
        try:
            self.set_job_folder(folder)
        except Exception as e:
            logger.exception("Failed to load job folder: %s", folder)
            messagebox.showerror("Error Loading Folder",
                                 f"Could not load job folder:\n\n{e}")

    @staticmethod
    def _get_folder_created_date(folder_path: str) -> str:
        """Return the folder's created date as 'YYYY-MM-DD', or '' on failure."""
        try:
            ctime = os.path.getctime(folder_path)
            return datetime.fromtimestamp(ctime).strftime("%Y-%m-%d")
        except OSError:
            return ""

    def _set_info_field(self, value_label, source_label, value, source):
        """Set an info field's value and the data-source caption beneath it.

        source: "name" (parsed from the folder name), "metadata" (derived from
        the folder's filesystem metadata), or "" (unknown / no value).
        """
        value_label.config(text=value or "-")
        if not value:
            source_label.config(text="")
        elif source == "name":
            source_label.config(text="Source: Folder name", fg=Theme.ACCENT_SUCCESS)
        elif source == "metadata":
            source_label.config(text="Source: Metadata", fg=Theme.ACCENT_WARNING)
        else:
            source_label.config(text="", fg=Theme.TEXT_TERTIARY)

    @staticmethod
    def _normalize_folder_key(name: str) -> str:
        """Normalize a folder name for tolerant matching: lowercase, drop a
        leading numeric/separator prefix (e.g. "4_"), and strip non-alphanumerics.
        So "4_ArtSetups", "4_Art Setups", "art_setups" and "ArtSetups" all map
        to "artsetups"."""
        s = name.strip().lower()
        s = re.sub(r'^[\d_\-.\s]+', '', s)   # drop leading "4_", "4 ", "4-", ...
        s = re.sub(r'[^a-z0-9]+', '', s)     # drop spaces/underscores/etc.
        return s

    def _scan_standard_folders(self):
        """Classify each standard subfolder against what's on disk.

        Returns a list of dicts: {canonical, status, actual} where status is
        'present' (exact), 'matched' (a name variant exists) or 'missing'.
        """
        existing = {}  # normalized key -> actual on-disk name
        try:
            for entry in os.listdir(self.job_folder_path):
                if os.path.isdir(os.path.join(self.job_folder_path, entry)):
                    existing.setdefault(self._normalize_folder_key(entry), entry)
        except OSError:
            pass

        result = []
        for canonical in STANDARD_SUBFOLDERS:
            key = self._normalize_folder_key(canonical)
            if os.path.isdir(os.path.join(self.job_folder_path, canonical)):
                result.append({'canonical': canonical, 'status': 'present',
                               'actual': canonical})
            elif key in existing:
                result.append({'canonical': canonical, 'status': 'matched',
                               'actual': existing[key]})
            else:
                result.append({'canonical': canonical, 'status': 'missing',
                               'actual': canonical})
        return result

    def _resolve_subfolder(self, canonical: str) -> str:
        """Path to the on-disk folder for a standard subfolder, tolerating name
        variants. Falls back to the canonical path if nothing matches."""
        if not self.job_folder_path:
            return canonical
        canonical_path = os.path.join(self.job_folder_path, canonical)
        if os.path.isdir(canonical_path):
            return canonical_path
        target = self._normalize_folder_key(canonical)
        try:
            for entry in os.listdir(self.job_folder_path):
                full = os.path.join(self.job_folder_path, entry)
                if os.path.isdir(full) and self._normalize_folder_key(entry) == target:
                    return full
        except OSError:
            pass
        return canonical_path

    def create_standard_folders(self):
        """Create missing standard subfolders, after confirming with the user.
        Existing name-variants are reused rather than duplicated."""
        if not self.job_folder_path:
            return

        scan = self._scan_standard_folders()
        to_create = [s['canonical'] for s in scan if s['status'] == 'missing']
        matched = [s for s in scan if s['status'] == 'matched']

        if not to_create:
            self.status_bar.set_message("All standard folders already exist", "info")
            self.refresh_folder_contents()
            return

        # Confirmation listing exactly what will be created and what is reused
        lines = ["Create the following folder(s) in:", self.job_folder_path, "",
                 "WILL CREATE:"]
        lines += [f"     • {name}" for name in to_create]
        if matched:
            lines += ["", "ALREADY PRESENT (will be used, not duplicated):"]
            lines += [f"     • {s['canonical']}  →  existing \"{s['actual']}\""
                      for s in matched]
        lines += ["", "Proceed?"]
        if not messagebox.askyesno("Create Standard Folders", "\n".join(lines)):
            return

        created = []
        for name in to_create:
            if ensure_directory(Path(os.path.join(self.job_folder_path, name))):
                created.append(name)
        self.status_bar.set_message(
            f"Created {len(created)} folder(s): {', '.join(created)}", "success")
        self.refresh_folder_contents()
        self.detect_revisions()

    def refresh_folder_contents(self):
        """Refresh the standard-folder status and the two file lists."""
        if not self.job_folder_path:
            self.folders_status_label.config(
                text="Select a job folder to see its contents.",
                fg=Theme.TEXT_SECONDARY)
            self.create_folders_btn.set_enabled(False)
            self._populate_file_list(self.artsetups_listbox, None)
            self._populate_file_list(self.proofs_listbox, None)
            return

        scan = self._scan_standard_folders()
        missing = [s['canonical'] for s in scan if s['status'] == 'missing']
        matched = [s for s in scan if s['status'] == 'matched']
        if missing:
            self.folders_status_label.config(
                text="Missing folder(s): " + ", ".join(missing),
                fg=Theme.ACCENT_WARNING)
            self.create_folders_btn.set_enabled(True)
        elif matched:
            note = "; ".join(f"{s['canonical']}→{s['actual']}" for s in matched)
            self.folders_status_label.config(
                text="All present (reusing existing: " + note + ")",
                fg=Theme.ACCENT_SUCCESS)
            self.create_folders_btn.set_enabled(False)
        else:
            self.folders_status_label.config(
                text="All 5 standard folders present.", fg=Theme.ACCENT_SUCCESS)
            self.create_folders_btn.set_enabled(False)

        self._populate_file_list(
            self.artsetups_listbox, self._resolve_subfolder(SUBFOLDER_ART_SETUPS))
        self._populate_file_list(
            self.proofs_listbox, self._resolve_subfolder(SUBFOLDER_PROOFS))

        # Sync the watch baseline so the poll doesn't immediately re-refresh
        self._last_folder_sig = self._folder_signature()

    def _folder_signature(self):
        """A cheap snapshot of the standard folders' presence and contents,
        used to detect on-disk changes between polls."""
        if not self.job_folder_path:
            return None
        sig = []
        for sub in STANDARD_SUBFOLDERS:
            path = os.path.join(self.job_folder_path, sub)
            if os.path.isdir(path):
                try:
                    names = tuple(sorted(os.listdir(path)))
                except OSError:
                    names = ("<unreadable>",)
                sig.append((sub, True, names))
            else:
                sig.append((sub, False, ()))
        return tuple(sig)

    def _poll_folder_contents(self):
        """Periodically re-read the job folder and refresh the UI if it changed
        on disk (e.g. files added/removed/renamed outside the app)."""
        try:
            sig = self._folder_signature()
            if sig != self._last_folder_sig:
                self._last_folder_sig = sig
                self.refresh_folder_contents()
        except Exception:
            logger.exception("Folder watch poll failed")
        finally:
            # Reschedule; ~2s feels live without hammering the disk
            self.root.after(2000, self._poll_folder_contents)

    def _populate_file_list(self, listbox, folder):
        """Fill a file listbox from a folder (None/missing -> placeholder)."""
        listbox.delete(0, tk.END)
        listbox._file_paths = []

        def placeholder(text):
            listbox.insert(tk.END, text)
            listbox._file_paths.append(None)
            listbox.itemconfig(0, fg=Theme.TEXT_TERTIARY)

        if not folder or not os.path.isdir(folder):
            placeholder("(folder not present)")
            return
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            placeholder("(could not read folder)")
            return
        files = [n for n in names if os.path.isfile(os.path.join(folder, n))]
        if not files:
            placeholder("(empty)")
            return
        for name in files:
            listbox.insert(tk.END, name)
            listbox._file_paths.append(os.path.join(folder, name))

    def _on_file_list_open(self, event):
        """Open the double-clicked file with the OS default application."""
        listbox = event.widget
        selection = listbox.curselection()
        if not selection:
            return
        paths = getattr(listbox, "_file_paths", [])
        idx = selection[0]
        if idx < len(paths) and paths[idx]:
            if open_file(paths[idx]):
                self.status_bar.set_message(
                    f"Opened {os.path.basename(paths[idx])}", "info")
            else:
                self.status_bar.set_message("Could not open file", "error")

    def set_job_folder(self, folder_path: str):
        """Set and parse the job folder"""
        self.job_folder_path = folder_path

        # Update display with the native path form (e.g. backslashes on Windows)
        # so it matches how the address would normally be typed/pasted.
        # set_text handles readonly + placeholder correctly.
        self.job_folder_display.set_text(os.path.normpath(folder_path))

        # Parse folder name
        folder_name = os.path.basename(folder_path)
        parsed = JobFolderParser.parse(folder_name)

        # Resolve the job date. Prefer the date encoded in the job number; if
        # the folder name has no date (old-style numeric jobs), fall back to the
        # folder's created-date metadata and flag it as such.
        job_date = parsed.job_date
        date_source = parsed.date_source  # "name" when parsed from the folder
        if not job_date:
            job_date = self._get_folder_created_date(folder_path)
            date_source = "metadata" if job_date else ""

        self.job_info = {
            "job_number": parsed.job_number,
            "customer": parsed.customer,
            "company": parsed.company,
            "sku": parsed.sku,
            "quantity": parsed.quantity,
            "po_number": parsed.po_number,
            "job_date": job_date,
            "date_source": date_source,
        }

        # Update info display. Job#, customer, company, SKU, qty and PO# are all
        # parsed from the folder name; the date may instead come from metadata.
        self._set_info_field(self.info_job, self.info_job_src, self.job_info.get("job_number"), "name")
        self._set_info_field(self.info_customer, self.info_customer_src, self.job_info.get("customer"), "name")
        self._set_info_field(self.info_company, self.info_company_src, self.job_info.get("company"), "name")
        self._set_info_field(self.info_sku, self.info_sku_src, self.job_info.get("sku"), "name")
        self._set_info_field(self.info_qty, self.info_qty_src, self.job_info.get("quantity"), "name")
        self._set_info_field(self.info_po, self.info_po_src, self.job_info.get("po_number"), "name")
        self._set_info_field(self.info_date, self.info_date_src, job_date, date_source)

        # Show standard-folder status and list current contents. Folders are no
        # longer auto-created here — use the "Create Folders" button. (The rename
        # service still creates a destination folder on demand if needed.)
        self.refresh_folder_contents()

        # Add to recent folders
        self.config.add_recent_folder(folder_path)
        save_config(self.config, CONFIG_FILE)

        self.detect_revisions()
        self.update_previews()
        self.job_loaded_label.config(text=f"✓ Loaded job: {folder_name}")
        logger.info(f"Set job folder: {folder_path}")

    def detect_revisions(self):
        """Detect existing revisions"""
        if not self.auto_revision_enabled.get() or not self.job_folder_path:
            return

        base_pattern = self._get_base_pattern()
        if not base_pattern:
            self.existing_rev_label.config(text="")
            return

        art_folder = self._resolve_subfolder(SUBFOLDER_ART_SETUPS)
        all_existing = self.revision_detector.get_existing_revisions(art_folder, base_pattern)

        if all_existing:
            self.existing_rev_label.config(text=f"Existing: {', '.join(all_existing)}")
            next_rev = self.revision_detector.find_next_revision(art_folder, base_pattern, ".psd")
            if next_rev in self.config.revisions:
                self.revision.current(self.config.revisions.index(next_rev))
            else:
                self.revision.set(next_rev)
        else:
            self.existing_rev_label.config(text="No existing files")
            self.revision.current(0)

    def _get_base_pattern(self) -> Optional[str]:
        """Get base pattern for filename"""
        job = self.job_info.get("job_number", "")
        sku = self.job_info.get("sku", "")
        art_ref = self.artwork_ref.get_value()

        if not job or not sku:
            return None

        parts = [job, sku]
        if art_ref:
            parts.append(f"({sanitize_filename(art_ref)})")

        return "_".join(parts)

    def _generate_filename(self, original_path: str, purpose: str) -> str:
        """Generate new filename"""
        return self.rename_service.generate_filename(
            original_path,
            self.job_info.get("job_number", ""),
            self.job_info.get("sku", ""),
            self.artwork_ref.get_value(),
            purpose,
            self.revision.get()
        )

    def update_previews(self):
        """Update preview list"""
        self.preview_listbox.delete(0, tk.END)

        if not self.job_folder_path:
            return

        # Main Design files
        for f in self.drop_main.get_files():
            new_name = self._generate_filename(f, "SOURCE")
            self.preview_listbox.insert(tk.END, f"* {os.path.basename(f)} -> {SUBFOLDER_ART_SETUPS}/{new_name}")

        # Proof files
        for f in self.drop_proof.get_files():
            new_name = self._generate_filename(f, "PROOF")
            self.preview_listbox.insert(tk.END, f"@ {os.path.basename(f)} -> {SUBFOLDER_PROOFS}/{new_name}")

        # Production files
        prod_type = self.production_type.get()
        for f in self.drop_production.get_files():
            new_name = self._generate_filename(f, prod_type)
            self.preview_listbox.insert(tk.END, f"# {os.path.basename(f)} -> {SUBFOLDER_ART_SETUPS}/{new_name}")

        # Update undo/redo button states
        self.undo_btn.set_enabled(self.undo_manager.can_undo())
        self.redo_btn.set_enabled(self.undo_manager.can_redo())

    def rename_files(self):
        """Rename and move files"""
        if not self.job_folder_path:
            messagebox.showwarning("No Job Folder", "Please select a job folder first.")
            return

        if not self.job_info.get("job_number"):
            messagebox.showwarning("Invalid Job", "Could not parse job number from folder name.")
            return

        # Collect all files
        files_to_process = []
        art_folder = self._resolve_subfolder(SUBFOLDER_ART_SETUPS)
        proof_folder = self._resolve_subfolder(SUBFOLDER_PROOFS)

        for f in self.drop_main.get_files():
            files_to_process.append({
                'path': f,
                'new_name': self._generate_filename(f, "SOURCE"),
                'dest': art_folder
            })

        for f in self.drop_proof.get_files():
            files_to_process.append({
                'path': f,
                'new_name': self._generate_filename(f, "PROOF"),
                'dest': proof_folder
            })

        prod_type = self.production_type.get()
        for f in self.drop_production.get_files():
            files_to_process.append({
                'path': f,
                'new_name': self._generate_filename(f, prod_type),
                'dest': art_folder
            })

        if not files_to_process:
            messagebox.showwarning("No Files", "Please add files to rename.")
            return

        if self.config.confirm_before_rename:
            if not messagebox.askyesno("Confirm", f"Rename and move {len(files_to_process)} file(s)?"):
                return

        # Get duplicate mode
        dup_mode_map = {"Skip": "skip", "Auto-increment": "increment", "Overwrite": "overwrite"}
        dup_mode = dup_mode_map.get(self.duplicate_mode.get(), "skip")

        # Process files
        self.status_bar.set_message("Renaming files...", "info")
        self.root.update()

        # Group by destination and process
        from collections import defaultdict
        by_dest = defaultdict(list)
        for f in files_to_process:
            by_dest[f['dest']].append({'path': f['path'], 'new_name': f['new_name']})

        total_success = 0
        total_errors = 0

        for dest, files in by_dest.items():
            session = self.rename_service.rename_files(
                files, dest, self.job_info.get("job_number", ""),
                duplicate_mode=dup_mode
            )
            total_success += session.success_count
            total_errors += session.error_count

        # Update stats
        self.files_renamed_this_session += total_success
        self.session_stats.config(text=f"Files renamed: {self.files_renamed_this_session}")

        # Update timer if clocked in
        if self.timer.is_clocked_in:
            self.timer.increment_files_renamed(total_success)

        # Show result
        if total_errors > 0:
            self.status_bar.set_message(f"Renamed {total_success} files with {total_errors} errors", "warning")
            messagebox.showwarning("Completed with Errors", 
                                  f"Renamed {total_success} file(s).\n{total_errors} file(s) had errors.")
        else:
            self.status_bar.set_message(f"Successfully renamed {total_success} files", "success")
            messagebox.showinfo("Success", f"Renamed {total_success} file(s)!")

        # Clear and refresh
        self.clear_all()
        self.detect_revisions()
        self.update_previews()

    def undo_rename(self):
        """Undo last rename operation"""
        if not self.undo_manager.can_undo():
            return

        success, message, count = self.undo_manager.undo()
        if success:
            self.status_bar.set_message(message, "success")
            self.files_renamed_this_session = max(0, self.files_renamed_this_session - count)
            self.session_stats.config(text=f"Files renamed: {self.files_renamed_this_session}")
        else:
            self.status_bar.set_message(message, "warning")
        
        self.update_previews()

    def redo_rename(self):
        """Redo last undone operation"""
        if not self.undo_manager.can_redo():
            return

        success, message, count = self.undo_manager.redo()
        if success:
            self.status_bar.set_message(message, "success")
            self.files_renamed_this_session += count
            self.session_stats.config(text=f"Files renamed: {self.files_renamed_this_session}")
        else:
            self.status_bar.set_message(message, "warning")
        
        self.update_previews()

    def clear_all(self):
        """Clear all drop zones"""
        self.drop_main.clear_files()
        self.drop_proof.clear_files()
        self.drop_production.clear_files()
        self.update_previews()
        self.status_bar.set_message("Cleared all files", "info")

    def handle_clock_in(self):
        """Handle clock in"""
        job = self.job_info.get("job_number", "")
        if not job:
            messagebox.showwarning("Job Required", "Please select a job folder before clocking in.")
            return

        success, message = self.timer.clock_in(job, self.job_folder_path)
        if success:
            self.timer_status.config(text=f"Working on: Job #{job}", fg=Theme.ACCENT_SUCCESS)
            self.timer_display.config(fg=Theme.ACCENT_SUCCESS)
            self.clock_in_btn.set_enabled(False)
            self.clock_out_btn.set_enabled(True)
            self.files_renamed_this_session = 0
            self.session_stats.config(text="Files renamed: 0")
            self.status_bar.set_message(f"Clocked in to Job #{job}", "success")
        messagebox.showinfo("Clock In", message)

    def handle_clock_out(self):
        """Handle clock out"""
        has_files = self.drop_main.has_files() or self.drop_proof.has_files() or self.drop_production.has_files()
        if has_files:
            if not messagebox.askyesno("Files Pending", "You have files waiting. Clock out anyway?"):
                return

        success, message, _ = self.timer.clock_out()
        if success:
            self.timer_status.config(text="Select a job folder to begin", fg=Theme.TEXT_SECONDARY)
            self.timer_display.config(text="00:00:00", fg=Theme.TEXT_TERTIARY)
            self.clock_in_btn.set_enabled(True)
            self.clock_out_btn.set_enabled(False)
            summary = f"{message}\n\nFiles renamed this session: {self.files_renamed_this_session}"
            self.status_bar.set_message("Clocked out", "info")
            messagebox.showinfo("Clock Out", summary)

    def view_time_logs(self):
        """Open time logs folder"""
        log_dir = SCRIPT_DIR / self.config.log_directory
        ensure_directory(log_dir)
        if open_folder(str(log_dir)):
            self.status_bar.set_message("Opened time logs folder", "info")
        else:
            self.status_bar.set_message("Could not open logs folder", "error")

    def open_settings(self):
        """Open settings dialog"""
        def on_settings_save(new_config: Config):
            self.config = new_config
            save_config(self.config, CONFIG_FILE)
            self.status_bar.set_message("Settings saved", "success")
            # Update UI with new settings
            self._refresh_after_settings()

        SettingsDialog(self.root, self.config, on_settings_save)

    def _refresh_after_settings(self):
        """Refresh UI after settings change"""
        # Update revision detector with new revisions
        self.revision_detector = RevisionDetector(self.config.revisions)
        
        # Update comboboxes
        self.revision['values'] = self.config.revisions
        if self.config.revisions:
            self.revision.current(0)
        
        self.production_type['values'] = self.config.production_types
        if self.config.production_types:
            self.production_type.current(0)

        # Re-detect revisions
        self.detect_revisions()
        self.update_previews()
        
        logger.info("UI refreshed after settings change")

    def _start_timer_update(self):
        """Start timer display updates"""
        self._update_timer_display()

    def _update_timer_display(self):
        """Update timer display"""
        if self.timer.is_clocked_in:
            elapsed = self.timer.get_elapsed_time()
            self.timer_display.config(text=elapsed)
            seconds = self.timer.get_elapsed_seconds()
            warning_mins = self.config.timer_settings.warning_minutes
            if seconds > warning_mins * 60:
                # Blink warning
                if int(seconds) % 2 == 0:
                    self.timer_display.config(fg=Theme.ACCENT_WARNING)
                else:
                    self.timer_display.config(fg=Theme.ACCENT_SUCCESS)
            else:
                self.timer_display.config(fg=Theme.ACCENT_SUCCESS)
        self.root.after(1000, self._update_timer_display)


def main():
    """Main entry point"""
    global HAS_DND
    
    # Check for drag-drop support on first run
    if not HAS_DND:
        # Check if user wants to install it
        check_and_install_dnd()
        # Try importing again in case it was just installed
        try:
            from tkinterdnd2 import TkinterDnD
            HAS_DND = True
        except ImportError:
            pass
    
    if HAS_DND:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = JobArtNamingHelper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
