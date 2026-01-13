"""
File Renamer Pro - Artwork Naming Tool with Time Tracking
Naming Convention: <Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>

Job Folder Structure:
- Main folder: Job#_CustomerName_Company_SKU x Qty_(PO#)
  - 1_TheirPOs
  - 2_OurDocs
  - 3_ProvidedArt
  - 4_ArtSetups      <- MainDesign & ProductionOutput files go here
  - 5_VirtualProofs  <- Proof files go here

Design: Dark theme "Creative Studio Tool" aesthetic
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
import time

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "config.json"
DEFAULT_LOG_DIR = SCRIPT_DIR / "time_logs"

# Subfolder names
SUBFOLDER_ART_SETUPS = "4_ArtSetups"
SUBFOLDER_PROOFS = "5_VirtualProofs"


# ============================================================================
# DESIGN SYSTEM - Creative Studio Dark Theme
# ============================================================================
class Theme:
    """Design tokens for the Creative Studio aesthetic"""

    # Core palette
    BG_PRIMARY = "#1a1a1f"
    BG_SECONDARY = "#242429"
    BG_TERTIARY = "#2d2d33"
    BG_ELEVATED = "#35353d"

    # Accent colors
    ACCENT_PRIMARY = "#ff6b35"    # Coral - primary actions
    ACCENT_SECONDARY = "#4ecdc4"  # Teal - info
    ACCENT_SUCCESS = "#45b764"    # Green
    ACCENT_WARNING = "#ffc857"    # Amber
    ACCENT_DANGER = "#ff4757"     # Red
    ACCENT_PURPLE = "#a855f7"     # Purple - for production

    # Drop zone colors
    DROP_MAIN_DESIGN = "#2a4858"      # Blue-teal for main design
    DROP_VIRTUAL_PROOF = "#3d2a4d"    # Purple for proofs
    DROP_PRODUCTION = "#2d3a2d"       # Green for production

    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a8"
    TEXT_TERTIARY = "#6b6b75"
    TEXT_ON_ACCENT = "#ffffff"

    # Borders
    BORDER_SUBTLE = "#3a3a42"
    BORDER_DEFAULT = "#4a4a55"
    BORDER_FOCUS = "#ff6b35"

    # Typography
    FONT_DISPLAY = ("Segoe UI", 11, "bold")
    FONT_BODY = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_MONO = ("Cascadia Code", 10)
    FONT_MONO_LARGE = ("Cascadia Code", 36, "bold")
    FONT_BUTTON = ("Segoe UI Semibold", 10)

    # Spacing
    PAD_XS = 4
    PAD_SM = 8
    PAD_MD = 12
    PAD_LG = 16
    PAD_XL = 24


def load_config():
    """Load configuration from JSON file"""
    default_config = {
        "product_skus": ["-- Select SKU --", "CUSTOM"],
        "production_types": ["PRINT", "CUTFILE", "SUBLIMATION", "DTF", "EMBROIDERY", "LASER"],
        "revisions": ["1", "2", "3", "4", "5", "FINAL"],
        "timer_settings": {
            "warning_minutes": 30,
            "reminder_interval_minutes": 15,
            "auto_save_log": True
        },
        "log_directory": "time_logs",
        "job_folder_settings": {
            "base_directory": "",
            "job_number_pattern": r"^(\d+)"
        }
    }

    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
    except Exception as e:
        print(f"Error loading config: {e}")

    return default_config


class JobFolderParser:
    """Parses job folder names to extract components"""

    @staticmethod
    def parse(folder_name):
        """
        Parse folder name format: Job#_CustomerName_Company_SKU x Qty_(PO#)
        Example: 12345_JohnDoe_AcmeCorp_MUG-11OZ x 100_(PO-98765)

        Returns dict with: job_number, customer, company, sku, quantity, po_number
        """
        result = {
            "job_number": "",
            "customer": "",
            "company": "",
            "sku": "",
            "quantity": "",
            "po_number": "",
            "raw": folder_name
        }

        if not folder_name:
            return result

        # Try to extract PO number from end (in parentheses or brackets)
        po_match = re.search(r'[\(\[]([^\)\]]+)[\)\]]$', folder_name)
        if po_match:
            result["po_number"] = po_match.group(1)
            folder_name = folder_name[:po_match.start()].strip('_- ')

        # Split by underscores
        parts = folder_name.split('_')

        if len(parts) >= 1:
            # First part is job number
            job_match = re.match(r'^(\d+)', parts[0])
            if job_match:
                result["job_number"] = job_match.group(1)

        if len(parts) >= 2:
            result["customer"] = parts[1]

        if len(parts) >= 3:
            result["company"] = parts[2]

        if len(parts) >= 4:
            # SKU x Quantity format
            sku_qty = '_'.join(parts[3:])  # Join remaining parts
            sku_match = re.match(r'(.+?)\s*[xX]\s*(\d+)', sku_qty)
            if sku_match:
                result["sku"] = sku_match.group(1).strip()
                result["quantity"] = sku_match.group(2)
            else:
                result["sku"] = sku_qty

        return result


class TimerManager:
    """Manages the clock in/out timer functionality"""

    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.is_clocked_in = False
        self.clock_in_time = None
        self.current_job = None
        self.current_job_folder = None
        self.elapsed_seconds = 0

    def clock_in(self, job_number, job_folder=None):
        if self.is_clocked_in:
            return False, "Already clocked in!"
        self.is_clocked_in = True
        self.clock_in_time = datetime.now()
        self.current_job = job_number
        self.current_job_folder = job_folder
        self.elapsed_seconds = 0
        return True, f"Clocked in at {self.clock_in_time.strftime('%I:%M %p')}"

    def clock_out(self):
        if not self.is_clocked_in:
            return False, "Not clocked in!", None
        clock_out_time = datetime.now()
        duration = clock_out_time - self.clock_in_time
        log_entry = {
            "job_number": self.current_job,
            "job_folder": str(self.current_job_folder) if self.current_job_folder else None,
            "clock_in": self.clock_in_time.isoformat(),
            "clock_out": clock_out_time.isoformat(),
            "duration_minutes": round(duration.total_seconds() / 60, 2),
            "date": self.clock_in_time.strftime("%Y-%m-%d")
        }
        self.save_log_entry(log_entry)
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.is_clocked_in = False
        self.clock_in_time = None
        self.current_job = None
        self.current_job_folder = None
        return True, f"Clocked out! Session: {duration_str}", log_entry

    def save_log_entry(self, entry):
        date_str = entry["date"]
        log_file = self.log_dir / f"timelog_{date_str}.json"
        entries = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    entries = json.load(f)
            except:
                entries = []
        entries.append(entry)
        with open(log_file, 'w') as f:
            json.dump(entries, f, indent=2)

    def get_elapsed_time(self):
        if not self.is_clocked_in or not self.clock_in_time:
            return "00:00:00"
        elapsed = datetime.now() - self.clock_in_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_elapsed_seconds(self):
        if not self.is_clocked_in or not self.clock_in_time:
            return 0
        return (datetime.now() - self.clock_in_time).total_seconds()


class RevisionDetector:
    """Handles automatic revision detection based on existing files"""

    def __init__(self, revision_list):
        self.revision_list = revision_list

    def find_next_revision(self, folder_path, base_pattern, extension):
        if not folder_path or not os.path.isdir(folder_path):
            return self.revision_list[0] if self.revision_list else "1"
        escaped_base = re.escape(base_pattern)
        pattern = re.compile(rf"^{escaped_base}_(\d+|FINAL){re.escape(extension)}$", re.IGNORECASE)
        found_revisions = []
        try:
            for filename in os.listdir(folder_path):
                match = pattern.match(filename)
                if match:
                    rev = match.group(1).upper()
                    found_revisions.append("FINAL" if rev == "FINAL" else rev)
        except:
            return self.revision_list[0] if self.revision_list else "1"
        if not found_revisions:
            return self.revision_list[0] if self.revision_list else "1"
        max_numeric = 0
        for rev in found_revisions:
            if rev != "FINAL":
                try:
                    if int(rev) > max_numeric:
                        max_numeric = int(rev)
                except:
                    pass
        next_rev = str(max_numeric + 1)
        if next_rev in self.revision_list:
            return next_rev
        return "FINAL" if max_numeric >= 5 and "FINAL" in self.revision_list else next_rev

    def get_existing_revisions(self, folder_path, base_pattern, extension):
        if not folder_path or not os.path.isdir(folder_path):
            return []
        escaped_base = re.escape(base_pattern)
        pattern = re.compile(rf"^{escaped_base}_(\d+|FINAL){re.escape(extension)}$", re.IGNORECASE)
        found = []
        try:
            for filename in os.listdir(folder_path):
                match = pattern.match(filename)
                if match:
                    found.append(match.group(1))
        except:
            pass
        return sorted(found, key=lambda x: (x != "FINAL", int(x) if x.isdigit() else 999))


# ============================================================================
# CUSTOM STYLED WIDGETS
# ============================================================================

class StyledButton(tk.Canvas):
    """Custom styled button with hover effects"""

    def __init__(self, parent, text, command=None, variant="primary", width=120, height=36, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.variant = variant
        self.width = width
        self.height = height
        self._enabled = True

        self.colors = {
            "primary": {"bg": Theme.ACCENT_PRIMARY, "bg_hover": "#ff8555", "fg": Theme.TEXT_ON_ACCENT,
                       "bg_disabled": Theme.BG_TERTIARY, "fg_disabled": Theme.TEXT_TERTIARY},
            "secondary": {"bg": Theme.BG_TERTIARY, "bg_hover": Theme.BG_ELEVATED, "fg": Theme.TEXT_PRIMARY,
                         "bg_disabled": Theme.BG_SECONDARY, "fg_disabled": Theme.TEXT_TERTIARY},
            "success": {"bg": Theme.ACCENT_SUCCESS, "bg_hover": "#55c774", "fg": Theme.TEXT_ON_ACCENT,
                       "bg_disabled": Theme.BG_TERTIARY, "fg_disabled": Theme.TEXT_TERTIARY},
            "danger": {"bg": Theme.ACCENT_DANGER, "bg_hover": "#ff5f6d", "fg": Theme.TEXT_ON_ACCENT,
                      "bg_disabled": Theme.BG_TERTIARY, "fg_disabled": Theme.TEXT_TERTIARY}
        }

        self.configure(bg=parent.cget('bg') if hasattr(parent, 'cget') else Theme.BG_PRIMARY)
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, hover=False):
        self.delete("all")
        colors = self.colors.get(self.variant, self.colors["primary"])
        if not self._enabled:
            bg, fg = colors["bg_disabled"], colors["fg_disabled"]
        else:
            bg = colors["bg_hover"] if hover else colors["bg"]
            fg = colors["fg"]
        r = 6
        points = [2+r, 2, self.width-2-r, 2, self.width-2, 2, self.width-2, 2+r,
                  self.width-2, self.height-2-r, self.width-2, self.height-2,
                  self.width-2-r, self.height-2, 2+r, self.height-2,
                  2, self.height-2, 2, self.height-2-r, 2, 2+r, 2, 2]
        self.create_polygon(points, smooth=True, fill=bg, outline="")
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=fg, font=Theme.FONT_BUTTON)

    def _on_enter(self, e):
        if self._enabled:
            self._draw(hover=True)
            self.config(cursor="hand2")

    def _on_leave(self, e):
        self._draw(hover=False)
        self.config(cursor="")

    def _on_click(self, e):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self._draw()


class SectionCard(tk.Frame):
    """A styled card container"""

    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)
        self.configure(highlightbackground=Theme.BORDER_SUBTLE, highlightthickness=1)

        if title:
            title_frame = tk.Frame(self, bg=Theme.BG_SECONDARY)
            title_frame.pack(fill="x", padx=Theme.PAD_MD, pady=(Theme.PAD_MD, Theme.PAD_SM))
            tk.Label(title_frame, text=title.upper(), font=("Segoe UI Semibold", 9),
                    fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY).pack(side="left")
            tk.Frame(self, bg=Theme.ACCENT_PRIMARY, height=2).pack(fill="x", padx=Theme.PAD_MD)

        self.content = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.content.pack(fill="both", expand=True, padx=Theme.PAD_MD, pady=Theme.PAD_MD)


class DropZone(tk.Frame):
    """A styled drop zone for files"""

    def __init__(self, parent, title, subtitle, color, icon_text="", **kwargs):
        super().__init__(parent, bg=color, highlightbackground=Theme.BORDER_DEFAULT,
                        highlightthickness=2, **kwargs)

        self.base_color = color
        self.files = []
        self.on_files_changed = None

        # Content
        content = tk.Frame(self, bg=color)
        content.pack(fill="both", expand=True, padx=Theme.PAD_SM, pady=Theme.PAD_SM)

        # Header
        header = tk.Frame(content, bg=color)
        header.pack(fill="x")

        if icon_text:
            tk.Label(header, text=icon_text, font=("Segoe UI", 14), fg=Theme.TEXT_PRIMARY, bg=color).pack(side="left")

        tk.Label(header, text=title, font=("Segoe UI Semibold", 11), fg=Theme.TEXT_PRIMARY, bg=color).pack(side="left", padx=(Theme.PAD_XS, 0))

        # Clear button
        self.clear_btn = tk.Label(header, text="✕", font=("Segoe UI", 10), fg=Theme.TEXT_TERTIARY,
                                  bg=color, cursor="hand2")
        self.clear_btn.pack(side="right")
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_files())

        # Subtitle
        tk.Label(content, text=subtitle, font=Theme.FONT_SMALL, fg=Theme.TEXT_TERTIARY, bg=color).pack(anchor="w")

        # File list
        self.file_frame = tk.Frame(content, bg=color)
        self.file_frame.pack(fill="both", expand=True, pady=(Theme.PAD_SM, 0))

        # Placeholder
        self.placeholder = tk.Label(self.file_frame, text="Drop files here", font=Theme.FONT_BODY,
                                    fg=Theme.TEXT_TERTIARY, bg=color)
        self.placeholder.pack(expand=True)

        # File listbox (hidden initially)
        self.listbox = tk.Listbox(self.file_frame, bg=color, fg=Theme.TEXT_PRIMARY,
                                  selectbackground=Theme.ACCENT_PRIMARY, highlightthickness=0,
                                  borderwidth=0, font=Theme.FONT_MONO, height=3)

        # Setup DnD
        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._handle_drop)
            self.dnd_bind('<<DragEnter>>', lambda e: self.config(highlightbackground=Theme.ACCENT_PRIMARY))
            self.dnd_bind('<<DragLeave>>', lambda e: self.config(highlightbackground=Theme.BORDER_DEFAULT))

    def _handle_drop(self, event):
        self.config(highlightbackground=Theme.BORDER_DEFAULT)
        files = self._parse_dropped(event.data)
        for f in files:
            if os.path.isfile(f) and f not in self.files:
                self.files.append(f)
        self._update_display()
        if self.on_files_changed:
            self.on_files_changed()

    def _parse_dropped(self, data):
        files = []
        if '{' in data:
            files.extend(re.findall(r'\{([^}]+)\}', data))
            data = re.sub(r'\{[^}]+\}', '', data)
            files.extend(data.split())
        else:
            files = data.replace('\n', ' ').split()
        return [f.strip() for f in files if f.strip()]

    def _update_display(self):
        if self.files:
            self.placeholder.pack_forget()
            self.listbox.pack(fill="both", expand=True)
            self.listbox.delete(0, tk.END)
            for f in self.files:
                self.listbox.insert(tk.END, os.path.basename(f))
        else:
            self.listbox.pack_forget()
            self.placeholder.pack(expand=True)

    def clear_files(self):
        self.files.clear()
        self._update_display()
        if self.on_files_changed:
            self.on_files_changed()

    def add_files_dialog(self):
        files = filedialog.askopenfilenames(title="Select Files", filetypes=[("All Files", "*.*")])
        for f in files:
            if f not in self.files:
                self.files.append(f)
        self._update_display()
        if self.on_files_changed:
            self.on_files_changed()

    def get_files(self):
        return self.files.copy()

    def has_files(self):
        return len(self.files) > 0


class StyledEntry(tk.Entry):
    """Custom styled entry"""

    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                        insertbackground=Theme.ACCENT_PRIMARY, relief="flat",
                        highlightthickness=2, highlightbackground=Theme.BORDER_SUBTLE,
                        highlightcolor=Theme.BORDER_FOCUS, font=Theme.FONT_BODY, **kwargs)
        self.placeholder = placeholder
        self._has_placeholder = False
        if placeholder:
            self._show_placeholder()
            self.bind("<FocusIn>", self._on_focus_in)
            self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        if not self.get():
            self._has_placeholder = True
            self.insert(0, self.placeholder)
            self.config(fg=Theme.TEXT_TERTIARY)

    def _on_focus_in(self, e):
        if self._has_placeholder:
            self.delete(0, tk.END)
            self.config(fg=Theme.TEXT_PRIMARY)
            self._has_placeholder = False

    def _on_focus_out(self, e):
        if not self.get():
            self._show_placeholder()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class FileRenamerPro:
    def __init__(self, root):
        self.root = root
        self.root.title("File Renamer Pro")
        self.root.geometry("950x900")
        self.root.resizable(True, True)
        self.root.configure(bg=Theme.BG_PRIMARY)

        self.config = load_config()

        log_dir = SCRIPT_DIR / self.config.get("log_directory", "time_logs")
        self.timer = TimerManager(log_dir)
        self.revision_detector = RevisionDetector(self.config["revisions"])

        # Job data
        self.job_folder_path = None
        self.job_info = {}
        self.files_renamed_this_session = 0

        self.auto_revision_enabled = tk.BooleanVar(value=True)

        self._setup_styles()
        self.setup_ui()
        self.start_timer_update()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dark.TCombobox", fieldbackground=Theme.BG_TERTIARY, background=Theme.BG_TERTIARY,
                       foreground=Theme.TEXT_PRIMARY, arrowcolor=Theme.TEXT_SECONDARY, borderwidth=0, padding=8)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", Theme.BG_TERTIARY)],
                 foreground=[("disabled", Theme.TEXT_TERTIARY)])
        style.configure("Dark.TCheckbutton", background=Theme.BG_SECONDARY, foreground=Theme.TEXT_SECONDARY,
                       font=Theme.FONT_SMALL)

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=Theme.BG_PRIMARY)
        main_frame.pack(fill="both", expand=True, padx=Theme.PAD_LG, pady=Theme.PAD_LG)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        self._create_header(main_frame)
        self._create_timer_section(main_frame)
        self._create_job_section(main_frame)
        self._create_drop_zones(main_frame)
        self._create_action_bar(main_frame)

    def _create_header(self, parent):
        header = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        header.grid(row=0, column=0, sticky="ew", pady=(0, Theme.PAD_MD))

        title_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        title_frame.pack(side="left")

        tk.Label(title_frame, text="FILE RENAMER", font=("Segoe UI Black", 18),
                fg=Theme.TEXT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")
        tk.Label(title_frame, text=" PRO", font=("Segoe UI Black", 18),
                fg=Theme.ACCENT_PRIMARY, bg=Theme.BG_PRIMARY).pack(side="left")

        tk.Label(header, text="Artwork Naming Tool", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_PRIMARY).pack(side="left", padx=(Theme.PAD_MD, 0), pady=(8, 0))

    def _create_timer_section(self, parent):
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
        card = SectionCard(parent, title="Job Details")
        card.grid(row=2, column=0, sticky="ew", pady=(0, Theme.PAD_MD))

        content = card.content

        # Job Folder Row
        folder_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        folder_row.pack(fill="x", pady=(0, Theme.PAD_SM))

        tk.Label(folder_row, text="JOB FOLDER", font=("Segoe UI Semibold", 9),
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        input_row = tk.Frame(folder_row, bg=Theme.BG_SECONDARY)
        input_row.pack(fill="x", pady=(Theme.PAD_XS, 0))

        self.job_folder_display = StyledEntry(input_row, placeholder="Select main job folder...")
        self.job_folder_display.pack(side="left", fill="x", expand=True, ipady=6)
        self.job_folder_display.config(state="readonly")

        browse_btn = StyledButton(input_row, text="BROWSE", command=self.browse_job_folder,
                                  variant="secondary", width=90, height=34)
        browse_btn.pack(side="right", padx=(Theme.PAD_SM, 0))

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

        tk.Label(ref_row, text="ARTWORK REFERENCE", font=("Segoe UI Semibold", 9),
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        self.artwork_ref = StyledEntry(ref_row, placeholder="Brief description (e.g., BlueDog, SunsetBeach)")
        self.artwork_ref.pack(fill="x", pady=(Theme.PAD_XS, 0), ipady=6)
        self.artwork_ref.bind('<KeyRelease>', lambda e: self.update_previews())

        # Revision row
        rev_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        rev_row.pack(fill="x", pady=(Theme.PAD_SM, 0))

        tk.Label(rev_row, text="REVISION", font=("Segoe UI Semibold", 9),
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(side="left")

        self.revision = ttk.Combobox(rev_row, values=self.config["revisions"], width=8,
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

    def _create_info_field(self, parent, label, value):
        """Create a labeled info field"""
        frame = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        frame.pack(side="left", fill="x", expand=True, padx=(0, Theme.PAD_MD))

        tk.Label(frame, text=label, font=("Segoe UI", 8), fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

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
        self.drop_main = DropZone(zones_frame, "Main Design", "→ 4_ArtSetups (SOURCE)",
                                  Theme.DROP_MAIN_DESIGN, icon_text="🎨")
        self.drop_main.grid(row=0, column=0, sticky="nsew", padx=(0, Theme.PAD_SM), pady=(0, Theme.PAD_SM))
        self.drop_main.on_files_changed = self.update_previews

        # Virtual Proof Zone
        self.drop_proof = DropZone(zones_frame, "Virtual Proof", "→ 5_VirtualProofs (PROOF)",
                                   Theme.DROP_VIRTUAL_PROOF, icon_text="👁")
        self.drop_proof.grid(row=0, column=1, sticky="nsew", padx=(0, Theme.PAD_SM), pady=(0, Theme.PAD_SM))
        self.drop_proof.on_files_changed = self.update_previews

        # Production Output Zone
        self.drop_production = DropZone(zones_frame, "Production Output", "→ 4_ArtSetups",
                                        Theme.DROP_PRODUCTION, icon_text="⚙")
        self.drop_production.grid(row=0, column=2, sticky="nsew", pady=(0, Theme.PAD_SM))
        self.drop_production.on_files_changed = self.update_previews

        # Production type selector
        prod_type_row = tk.Frame(content, bg=Theme.BG_SECONDARY)
        prod_type_row.pack(fill="x", pady=(0, Theme.PAD_SM))

        tk.Label(prod_type_row, text="Production Type:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY).pack(side="left")

        self.production_type = ttk.Combobox(prod_type_row, values=self.config.get("production_types", ["PRINT"]),
                                            width=15, state="readonly", style="Dark.TCombobox")
        self.production_type.pack(side="left", padx=(Theme.PAD_SM, 0), ipady=2)
        self.production_type.current(0)
        self.production_type.bind("<<ComboboxSelected>>", lambda e: self.update_previews())

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
        tk.Label(btn_row, text=dnd_text, font=Theme.FONT_SMALL,
                fg=Theme.ACCENT_SUCCESS if HAS_DND else Theme.ACCENT_WARNING, bg=Theme.BG_SECONDARY).pack(side="right")

        # Preview section
        tk.Frame(content, bg=Theme.BORDER_SUBTLE, height=1).pack(fill="x", pady=Theme.PAD_MD)

        tk.Label(content, text="PREVIEW", font=("Segoe UI Semibold", 9),
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        preview_frame = tk.Frame(content, bg=Theme.BG_TERTIARY)
        preview_frame.pack(fill="x", pady=(Theme.PAD_XS, 0))

        self.preview_listbox = tk.Listbox(preview_frame, bg=Theme.BG_TERTIARY, fg=Theme.ACCENT_SECONDARY,
                                          highlightthickness=0, borderwidth=0, font=("Cascadia Code", 9), height=5)
        self.preview_listbox.pack(fill="both", expand=True, padx=Theme.PAD_SM, pady=Theme.PAD_SM)

    def _create_action_bar(self, parent):
        action_bar = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        action_bar.grid(row=4, column=0, sticky="ew")

        left_frame = tk.Frame(action_bar, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left")

        StyledButton(left_frame, text="VIEW LOGS", command=self.view_time_logs,
                    variant="secondary", width=100, height=38).pack(side="left", padx=(0, Theme.PAD_SM))
        StyledButton(left_frame, text="CLEAR ALL", command=self.clear_all,
                    variant="secondary", width=100, height=38).pack(side="left")

        self.rename_btn = StyledButton(action_bar, text="RENAME & MOVE FILES",
                                       command=self.rename_files, variant="primary", width=180, height=44)
        self.rename_btn.pack(side="right")

    # =========================================================================
    # BUSINESS LOGIC
    # =========================================================================

    def browse_job_folder(self):
        base_dir = self.config.get("job_folder_settings", {}).get("base_directory", "")
        if not base_dir or not os.path.isdir(base_dir):
            base_dir = None
        folder = filedialog.askdirectory(title="Select Main Job Folder", initialdir=base_dir)
        if folder:
            self.set_job_folder(folder)

    def set_job_folder(self, folder_path):
        self.job_folder_path = folder_path

        # Update display
        self.job_folder_display.config(state="normal")
        self.job_folder_display.delete(0, tk.END)
        self.job_folder_display.insert(0, folder_path)
        self.job_folder_display.config(state="readonly", fg=Theme.TEXT_PRIMARY)

        # Parse folder name
        folder_name = os.path.basename(folder_path)
        self.job_info = JobFolderParser.parse(folder_name)

        # Update info display
        self.info_job.config(text=self.job_info.get("job_number") or "-")
        self.info_customer.config(text=self.job_info.get("customer") or "-")
        self.info_company.config(text=self.job_info.get("company") or "-")
        self.info_sku.config(text=self.job_info.get("sku") or "-")
        self.info_qty.config(text=self.job_info.get("quantity") or "-")
        self.info_po.config(text=self.job_info.get("po_number") or "-")

        # Check for subfolders
        art_setups = os.path.join(folder_path, SUBFOLDER_ART_SETUPS)
        proofs = os.path.join(folder_path, SUBFOLDER_PROOFS)

        if not os.path.isdir(art_setups):
            os.makedirs(art_setups, exist_ok=True)
        if not os.path.isdir(proofs):
            os.makedirs(proofs, exist_ok=True)

        self.detect_revisions()
        self.update_previews()

    def detect_revisions(self):
        if not self.auto_revision_enabled.get() or not self.job_folder_path:
            return

        base_pattern = self._get_base_pattern()
        if not base_pattern:
            self.existing_rev_label.config(text="")
            return

        # Check in ArtSetups folder
        art_folder = os.path.join(self.job_folder_path, SUBFOLDER_ART_SETUPS)
        extensions = [".psd", ".ai", ".pdf", ".png", ".jpg", ".tif"]

        all_existing = []
        for ext in extensions:
            existing = self.revision_detector.get_existing_revisions(art_folder, base_pattern, ext)
            all_existing.extend(existing)
        all_existing = list(set(all_existing))

        if all_existing:
            sorted_revs = sorted(all_existing, key=lambda x: (x != "FINAL", int(x) if x.isdigit() else 999))
            self.existing_rev_label.config(text=f"Existing: {', '.join(sorted_revs)}")
            next_rev = self.revision_detector.find_next_revision(art_folder, base_pattern, ".psd")
            if next_rev in self.config["revisions"]:
                self.revision.current(self.config["revisions"].index(next_rev))
            else:
                self.revision.set(next_rev)
        else:
            self.existing_rev_label.config(text="No existing files")
            self.revision.current(0)

    def _get_base_pattern(self):
        job = self.job_info.get("job_number", "")
        sku = self.job_info.get("sku", "")
        art_ref = self.artwork_ref.get().strip()

        if not job or not sku:
            return None

        parts = [job, sku]
        if art_ref:
            parts.append(f"({art_ref})")

        return "_".join(parts)

    def _generate_filename(self, original_path, purpose):
        """Generate new filename for a file"""
        _, ext = os.path.splitext(original_path)

        job = self.job_info.get("job_number", "")
        sku = self.job_info.get("sku", "")
        art_ref = self.artwork_ref.get().strip()
        rev = self.revision.get()

        parts = []
        if job:
            parts.append(job)
        if sku:
            parts.append(sku)
        if art_ref:
            parts.append(f"({art_ref})")
        if purpose:
            parts.append(purpose)
        if rev:
            parts.append(rev)

        if not parts:
            return os.path.basename(original_path)

        return "_".join(parts) + ext

    def update_previews(self):
        self.preview_listbox.delete(0, tk.END)

        if not self.job_folder_path:
            return

        # Main Design files
        for f in self.drop_main.get_files():
            new_name = self._generate_filename(f, "SOURCE")
            self.preview_listbox.insert(tk.END, f"🎨 {os.path.basename(f)} → {SUBFOLDER_ART_SETUPS}/{new_name}")

        # Proof files
        for f in self.drop_proof.get_files():
            new_name = self._generate_filename(f, "PROOF")
            self.preview_listbox.insert(tk.END, f"👁 {os.path.basename(f)} → {SUBFOLDER_PROOFS}/{new_name}")

        # Production files
        prod_type = self.production_type.get()
        for f in self.drop_production.get_files():
            new_name = self._generate_filename(f, prod_type)
            self.preview_listbox.insert(tk.END, f"⚙ {os.path.basename(f)} → {SUBFOLDER_ART_SETUPS}/{new_name}")

    def rename_files(self):
        if not self.job_folder_path:
            messagebox.showwarning("No Job Folder", "Please select a job folder first.")
            return

        if not self.job_info.get("job_number"):
            messagebox.showwarning("Invalid Job", "Could not parse job number from folder name.")
            return

        main_files = self.drop_main.get_files()
        proof_files = self.drop_proof.get_files()
        prod_files = self.drop_production.get_files()

        total = len(main_files) + len(proof_files) + len(prod_files)
        if total == 0:
            messagebox.showwarning("No Files", "Please add files to rename.")
            return

        if not messagebox.askyesno("Confirm", f"Rename and move {total} file(s)?"):
            return

        renamed = 0
        errors = []

        art_folder = os.path.join(self.job_folder_path, SUBFOLDER_ART_SETUPS)
        proof_folder = os.path.join(self.job_folder_path, SUBFOLDER_PROOFS)

        # Ensure folders exist
        os.makedirs(art_folder, exist_ok=True)
        os.makedirs(proof_folder, exist_ok=True)

        import shutil

        # Process main design files
        for f in main_files:
            try:
                new_name = self._generate_filename(f, "SOURCE")
                new_path = os.path.join(art_folder, new_name)
                if os.path.exists(new_path):
                    errors.append(f"{os.path.basename(f)}: Target exists")
                    continue
                shutil.move(f, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"{os.path.basename(f)}: {str(e)}")

        # Process proof files
        for f in proof_files:
            try:
                new_name = self._generate_filename(f, "PROOF")
                new_path = os.path.join(proof_folder, new_name)
                if os.path.exists(new_path):
                    errors.append(f"{os.path.basename(f)}: Target exists")
                    continue
                shutil.move(f, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"{os.path.basename(f)}: {str(e)}")

        # Process production files
        prod_type = self.production_type.get()
        for f in prod_files:
            try:
                new_name = self._generate_filename(f, prod_type)
                new_path = os.path.join(art_folder, new_name)
                if os.path.exists(new_path):
                    errors.append(f"{os.path.basename(f)}: Target exists")
                    continue
                shutil.move(f, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"{os.path.basename(f)}: {str(e)}")

        self.files_renamed_this_session += renamed
        self.session_stats.config(text=f"Files renamed: {self.files_renamed_this_session}")

        if errors:
            error_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more"
            messagebox.showwarning("Completed with Errors", f"Renamed {renamed} file(s).\n\nErrors:\n{error_msg}")
        else:
            messagebox.showinfo("Success", f"Renamed {renamed} file(s)!")

        # Clear drop zones
        self.clear_all()
        self.detect_revisions()

    def clear_all(self):
        self.drop_main.clear_files()
        self.drop_proof.clear_files()
        self.drop_production.clear_files()
        self.update_previews()

    def handle_clock_in(self):
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
        messagebox.showinfo("Clock In", message)

    def handle_clock_out(self):
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
            messagebox.showinfo("Clock Out", summary)

    def view_time_logs(self):
        log_dir = SCRIPT_DIR / self.config.get("log_directory", "time_logs")
        log_dir.mkdir(exist_ok=True)
        os.startfile(str(log_dir))

    def start_timer_update(self):
        self.update_timer_display()

    def update_timer_display(self):
        if self.timer.is_clocked_in:
            elapsed = self.timer.get_elapsed_time()
            self.timer_display.config(text=elapsed)
            seconds = self.timer.get_elapsed_seconds()
            warning_mins = self.config["timer_settings"]["warning_minutes"]
            if seconds > warning_mins * 60:
                if int(seconds) % 2 == 0:
                    self.timer_display.config(fg=Theme.ACCENT_WARNING)
                else:
                    self.timer_display.config(fg=Theme.ACCENT_SUCCESS)
            else:
                self.timer_display.config(fg=Theme.ACCENT_SUCCESS)
        self.root.after(1000, self.update_timer_display)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    try:
        icon_path = SCRIPT_DIR / "app_icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except:
        pass

    app = FileRenamerPro(root)
    root.mainloop()


if __name__ == "__main__":
    main()
