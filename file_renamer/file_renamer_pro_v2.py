"""
File Renamer Pro v2 - Artwork Naming Tool with Time Tracking
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
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
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
from src.utils import open_folder, sanitize_filename, ensure_directory
from src.widgets import (
    StyledButton, SectionCard, DropZone, StyledEntry, 
    StatusBar, ScrollableFrame, Tooltip
)
from src.settings_dialog import SettingsDialog

# Try to import drag-drop support
try:
    from tkinterdnd2 import TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Configuration paths
CONFIG_FILE = SCRIPT_DIR / "config.json"

# Subfolder names
SUBFOLDER_ART_SETUPS = "4_ArtSetups"
SUBFOLDER_PROOFS = "5_VirtualProofs"


class FileRenamerPro:
    """Main application class for File Renamer Pro"""

    def __init__(self, root):
        self.root = root
        self.root.title("File Renamer Pro")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)
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

        # Setup UI
        self._setup_styles()
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._start_timer_update()

        # Set icon
        self._set_icon()

        logger.info("File Renamer Pro initialized")

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

        tk.Label(title_frame, text="FILE RENAMER", font=Theme.FONT_TITLE,
                fg=Theme.TEXT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")
        tk.Label(title_frame, text=" PRO", font=Theme.FONT_TITLE,
                fg=Theme.ACCENT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")

        tk.Label(header, text="Artwork Naming Tool v2.0", font=Theme.FONT_SMALL,
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

        # Recent folders dropdown
        if self.config.job_folder_settings.recent_folders:
            self.recent_var = tk.StringVar(value="Recent...")
            recent_menu = ttk.Combobox(label_row, textvariable=self.recent_var,
                                       values=["Recent..."] + self.config.job_folder_settings.recent_folders[:5],
                                       width=20, state="readonly", style="Dark.TCombobox")
            recent_menu.pack(side="right")
            recent_menu.bind("<<ComboboxSelected>>", self._on_recent_selected)

        input_row = tk.Frame(folder_row, bg=Theme.BG_SECONDARY)
        input_row.pack(fill="x", pady=(Theme.PAD_XS, 0))

        self.job_folder_display = StyledEntry(input_row, placeholder="Select main job folder... (Ctrl+O)")
        self.job_folder_display.pack(side="left", fill="x", expand=True, ipady=6)
        self.job_folder_display.config(state="readonly")

        browse_btn = StyledButton(input_row, text="BROWSE", command=self.browse_job_folder,
                                  variant="secondary", width=90, height=34)
        browse_btn.pack(side="right", padx=(Theme.PAD_SM, 0))
        browse_btn.set_tooltip("Browse for job folder (Ctrl+O)")

        # Parsed info display
        self.job_info_frame = tk.Frame(content, bg=Theme.BG_SECONDARY)
        self.job_info_frame.pack(fill="x", pady=(Theme.PAD_SM, 0))

        # Info grid
        info_grid = tk.Frame(self.job_info_frame, bg=Theme.BG_SECONDARY)
        info_grid.pack(fill="x")

        # Row 1: Job#, Customer, Company
        row1 = tk.Frame(info_grid, bg=Theme.BG_SECONDARY)
        row1.pack(fill="x", pady=(0, Theme.PAD_SM))

        self.info_job = self._create_info_field(row1, "JOB #", "-")
        self.info_customer = self._create_info_field(row1, "CUSTOMER", "-")
        self.info_company = self._create_info_field(row1, "COMPANY", "-")

        # Row 2: SKU, Qty, PO#
        row2 = tk.Frame(info_grid, bg=Theme.BG_SECONDARY)
        row2.pack(fill="x")

        self.info_sku = self._create_info_field(row2, "SKU", "-")
        self.info_qty = self._create_info_field(row2, "QTY", "-")
        self.info_po = self._create_info_field(row2, "PO #", "-")

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
        """Create a labeled info field"""
        frame = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        frame.pack(side="left", fill="x", expand=True, padx=(0, Theme.PAD_MD))

        tk.Label(frame, text=label, font=("Segoe UI", 8), fg=Theme.TEXT_TERTIARY, 
                bg=Theme.BG_SECONDARY).pack(anchor="w")

        value_label = tk.Label(frame, text=value, font=("Segoe UI Semibold", 11),
                               fg=Theme.TEXT_PRIMARY, bg=Theme.BG_SECONDARY)
        value_label.pack(anchor="w")

        return value_label

    def _create_drop_zones(self, parent):
        """Create the three drop zones"""
        card = SectionCard(parent, title="Files to Rename")
        card.grid(row=3, column=0, sticky="nsew", pady=(0, Theme.PAD_MD))

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
        action_bar.grid(row=4, column=0, sticky="ew", pady=(0, Theme.PAD_SM))

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
            self.set_job_folder(folder)

    def _on_recent_selected(self, event):
        """Handle recent folder selection"""
        selected = self.recent_var.get()
        if selected and selected != "Recent..." and os.path.isdir(selected):
            self.set_job_folder(selected)
        self.recent_var.set("Recent...")

    def set_job_folder(self, folder_path: str):
        """Set and parse the job folder"""
        self.job_folder_path = folder_path

        # Update display
        self.job_folder_display.config(state="normal")
        self.job_folder_display.delete(0, tk.END)
        self.job_folder_display.insert(0, folder_path)
        self.job_folder_display.config(state="readonly", fg=Theme.TEXT_PRIMARY)

        # Parse folder name
        folder_name = os.path.basename(folder_path)
        parsed = JobFolderParser.parse(folder_name)
        self.job_info = {
            "job_number": parsed.job_number,
            "customer": parsed.customer,
            "company": parsed.company,
            "sku": parsed.sku,
            "quantity": parsed.quantity,
            "po_number": parsed.po_number,
        }

        # Update info display
        self.info_job.config(text=self.job_info.get("job_number") or "-")
        self.info_customer.config(text=self.job_info.get("customer") or "-")
        self.info_company.config(text=self.job_info.get("company") or "-")
        self.info_sku.config(text=self.job_info.get("sku") or "-")
        self.info_qty.config(text=self.job_info.get("quantity") or "-")
        self.info_po.config(text=self.job_info.get("po_number") or "-")

        # Ensure subfolders exist
        art_setups = os.path.join(folder_path, SUBFOLDER_ART_SETUPS)
        proofs = os.path.join(folder_path, SUBFOLDER_PROOFS)
        ensure_directory(Path(art_setups))
        ensure_directory(Path(proofs))

        # Add to recent folders
        self.config.add_recent_folder(folder_path)
        save_config(self.config, CONFIG_FILE)

        self.detect_revisions()
        self.update_previews()
        self.status_bar.set_message(f"Loaded job: {folder_name}", "success")
        logger.info(f"Set job folder: {folder_path}")

    def detect_revisions(self):
        """Detect existing revisions"""
        if not self.auto_revision_enabled.get() or not self.job_folder_path:
            return

        base_pattern = self._get_base_pattern()
        if not base_pattern:
            self.existing_rev_label.config(text="")
            return

        art_folder = os.path.join(self.job_folder_path, SUBFOLDER_ART_SETUPS)
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
        art_folder = os.path.join(self.job_folder_path, SUBFOLDER_ART_SETUPS)
        proof_folder = os.path.join(self.job_folder_path, SUBFOLDER_PROOFS)

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
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = FileRenamerPro(root)
    root.mainloop()


if __name__ == "__main__":
    main()
