"""
Settings Dialog for File Renamer Pro
GUI for editing configuration options
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable

from .theme import Theme
from .config import Config
from .widgets import StyledButton, StyledEntry


class SettingsDialog(tk.Toplevel):
    """Settings dialog window for editing configuration"""

    def __init__(self, parent, config: Config, on_save: Optional[Callable[[Config], None]] = None):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save
        self.result: Optional[Config] = None

        # Window setup
        self.title("Settings")
        self.geometry("600x650")
        self.resizable(True, True)
        self.configure(bg=Theme.BG_PRIMARY)
        
        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui()

    def _setup_ui(self):
        """Setup the settings UI"""
        # Main container with scrollbar
        main_frame = tk.Frame(self, bg=Theme.BG_PRIMARY)
        main_frame.pack(fill="both", expand=True, padx=Theme.PAD_LG, pady=Theme.PAD_LG)

        # Create notebook for tabs
        style = ttk.Style()
        style.configure("Dark.TNotebook", background=Theme.BG_PRIMARY)
        style.configure("Dark.TNotebook.Tab", 
                       background=Theme.BG_SECONDARY, 
                       foreground=Theme.TEXT_PRIMARY,
                       padding=[12, 6])
        style.map("Dark.TNotebook.Tab",
                 background=[("selected", Theme.BG_TERTIARY)],
                 foreground=[("selected", Theme.ACCENT_PRIMARY)])

        self.notebook = ttk.Notebook(main_frame, style="Dark.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # Create tabs
        self._create_general_tab()
        self._create_naming_tab()
        self._create_timer_tab()
        self._create_advanced_tab()

        # Button bar
        btn_frame = tk.Frame(main_frame, bg=Theme.BG_PRIMARY)
        btn_frame.pack(fill="x", pady=(Theme.PAD_LG, 0))

        StyledButton(btn_frame, text="CANCEL", command=self._on_cancel,
                    variant="secondary", width=100, height=38).pack(side="right", padx=(Theme.PAD_SM, 0))
        StyledButton(btn_frame, text="SAVE", command=self._on_save,
                    variant="primary", width=100, height=38).pack(side="right")
        StyledButton(btn_frame, text="RESET DEFAULTS", command=self._on_reset,
                    variant="secondary", width=130, height=38).pack(side="left")

    def _create_tab_frame(self, name: str) -> tk.Frame:
        """Create a tab frame with consistent styling"""
        frame = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)
        self.notebook.add(frame, text=name)
        
        inner = tk.Frame(frame, bg=Theme.BG_SECONDARY)
        inner.pack(fill="both", expand=True, padx=Theme.PAD_MD, pady=Theme.PAD_MD)
        return inner

    def _create_section_label(self, parent, text: str):
        """Create a section label"""
        tk.Label(parent, text=text.upper(), font=("Segoe UI Semibold", 9),
                fg=Theme.ACCENT_PRIMARY, bg=Theme.BG_SECONDARY).pack(anchor="w", pady=(Theme.PAD_MD, Theme.PAD_XS))

    def _create_field(self, parent, label: str, widget_type: str = "entry", 
                     values: list = None, width: int = None) -> tk.Widget:
        """Create a labeled field"""
        row = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        row.pack(fill="x", pady=Theme.PAD_XS)

        tk.Label(row, text=label, font=Theme.FONT_BODY, fg=Theme.TEXT_SECONDARY, 
                bg=Theme.BG_SECONDARY, width=25, anchor="w").pack(side="left")

        if widget_type == "entry":
            widget = StyledEntry(row)
            widget.pack(side="left", fill="x", expand=True, ipady=4)
        elif widget_type == "spinbox":
            widget = tk.Spinbox(row, from_=0, to=999, width=width or 10,
                               bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                               buttonbackground=Theme.BG_TERTIARY,
                               highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
            widget.pack(side="left")
        elif widget_type == "combobox":
            widget = ttk.Combobox(row, values=values or [], width=width or 20,
                                 state="readonly", style="Dark.TCombobox")
            widget.pack(side="left")
        elif widget_type == "checkbox":
            var = tk.BooleanVar()
            widget = ttk.Checkbutton(row, variable=var, style="Dark.TCheckbutton")
            widget.pack(side="left")
            widget.var = var  # Store reference to variable
        elif widget_type == "text":
            widget = tk.Text(row, height=4, width=width or 40,
                           bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                           insertbackground=Theme.ACCENT_PRIMARY,
                           highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
            widget.pack(side="left", fill="x", expand=True)
        elif widget_type == "browse":
            inner = tk.Frame(row, bg=Theme.BG_SECONDARY)
            inner.pack(side="left", fill="x", expand=True)
            entry = StyledEntry(inner)
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            btn = StyledButton(inner, text="...", variant="secondary", width=40, height=28,
                              command=lambda e=entry: self._browse_folder(e))
            btn.pack(side="left", padx=(Theme.PAD_XS, 0))
            widget = entry
        else:
            widget = tk.Label(row, text="Unknown", bg=Theme.BG_SECONDARY)
            widget.pack(side="left")

        return widget

    def _browse_folder(self, entry_widget):
        """Browse for a folder and set entry value"""
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            entry_widget.config(state="normal")
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)

    def _create_general_tab(self):
        """Create General settings tab"""
        tab = self._create_tab_frame("General")

        self._create_section_label(tab, "Job Folder Settings")
        
        self.base_dir_entry = self._create_field(tab, "Default Job Folder Location:", "browse")
        self.base_dir_entry.delete(0, tk.END)
        self.base_dir_entry.insert(0, self.config.job_folder_settings.base_directory)

        self.max_recent = self._create_field(tab, "Max Recent Folders:", "spinbox", width=8)
        self.max_recent.delete(0, tk.END)
        self.max_recent.insert(0, str(self.config.job_folder_settings.max_recent))

        self._create_section_label(tab, "Behavior")

        self.confirm_rename = self._create_field(tab, "Confirm before rename:", "checkbox")
        self.confirm_rename.var.set(self.config.confirm_before_rename)

        self.show_tooltips = self._create_field(tab, "Show tooltips:", "checkbox")
        self.show_tooltips.var.set(self.config.show_tooltips)

        self.backup_files = self._create_field(tab, "Backup files before rename:", "checkbox")
        self.backup_files.var.set(self.config.backup_before_rename)

        self._create_section_label(tab, "Duplicate File Handling")

        self.dup_mode = self._create_field(tab, "Default duplicate mode:", "combobox",
                                          values=["ask", "skip", "increment", "overwrite"])
        self.dup_mode.set(self.config.duplicate_handling.mode)

    def _create_naming_tab(self):
        """Create Naming Options tab"""
        tab = self._create_tab_frame("Naming")

        self._create_section_label(tab, "Product SKUs")
        tk.Label(tab, text="One SKU per line:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")
        
        self.skus_text = tk.Text(tab, height=6, bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                                insertbackground=Theme.ACCENT_PRIMARY,
                                highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE,
                                font=Theme.FONT_MONO)
        self.skus_text.pack(fill="x", pady=Theme.PAD_XS)
        self.skus_text.insert("1.0", "\n".join(self.config.product_skus))

        self._create_section_label(tab, "Production Types")
        tk.Label(tab, text="One type per line:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")
        
        self.prod_types_text = tk.Text(tab, height=5, bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                                      insertbackground=Theme.ACCENT_PRIMARY,
                                      highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE,
                                      font=Theme.FONT_MONO)
        self.prod_types_text.pack(fill="x", pady=Theme.PAD_XS)
        self.prod_types_text.insert("1.0", "\n".join(self.config.production_types))

        self._create_section_label(tab, "Revision Options")
        tk.Label(tab, text="One revision per line:", font=Theme.FONT_SMALL,
                fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")
        
        self.revisions_text = tk.Text(tab, height=4, bg=Theme.BG_TERTIARY, fg=Theme.TEXT_PRIMARY,
                                     insertbackground=Theme.ACCENT_PRIMARY,
                                     highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE,
                                     font=Theme.FONT_MONO)
        self.revisions_text.pack(fill="x", pady=Theme.PAD_XS)
        self.revisions_text.insert("1.0", "\n".join(self.config.revisions))

    def _create_timer_tab(self):
        """Create Timer settings tab"""
        tab = self._create_tab_frame("Timer")

        self._create_section_label(tab, "Timer Warnings")

        self.warning_mins = self._create_field(tab, "Warning after (minutes):", "spinbox", width=8)
        self.warning_mins.delete(0, tk.END)
        self.warning_mins.insert(0, str(self.config.timer_settings.warning_minutes))

        self.reminder_mins = self._create_field(tab, "Reminder interval (minutes):", "spinbox", width=8)
        self.reminder_mins.delete(0, tk.END)
        self.reminder_mins.insert(0, str(self.config.timer_settings.reminder_interval_minutes))

        self._create_section_label(tab, "Logging")

        self.log_dir_entry = self._create_field(tab, "Log directory:", "entry")
        self.log_dir_entry.delete(0, tk.END)
        self.log_dir_entry.insert(0, self.config.log_directory)

        self.auto_save_log = self._create_field(tab, "Auto-save time logs:", "checkbox")
        self.auto_save_log.var.set(self.config.timer_settings.auto_save_log)

    def _create_advanced_tab(self):
        """Create Advanced settings tab"""
        tab = self._create_tab_frame("Advanced")

        self._create_section_label(tab, "Job Number Pattern")
        tk.Label(tab, text="Regular expression for extracting job number from folder name:",
                font=Theme.FONT_SMALL, fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        self.job_pattern_entry = self._create_field(tab, "Pattern:", "entry")
        self.job_pattern_entry.delete(0, tk.END)
        self.job_pattern_entry.insert(0, self.config.job_folder_settings.job_number_pattern)

        self._create_section_label(tab, "Auto-increment Format")
        tk.Label(tab, text="Format for auto-incrementing duplicate files (use {n} for number):",
                font=Theme.FONT_SMALL, fg=Theme.TEXT_TERTIARY, bg=Theme.BG_SECONDARY).pack(anchor="w")

        self.increment_format = self._create_field(tab, "Format:", "entry")
        self.increment_format.delete(0, tk.END)
        self.increment_format.insert(0, self.config.duplicate_handling.auto_increment_format)

        self._create_section_label(tab, "Clear Data")

        clear_frame = tk.Frame(tab, bg=Theme.BG_SECONDARY)
        clear_frame.pack(fill="x", pady=Theme.PAD_SM)

        StyledButton(clear_frame, text="Clear Recent Folders", 
                    command=self._clear_recent_folders,
                    variant="secondary", width=150, height=32).pack(side="left", padx=(0, Theme.PAD_SM))

        StyledButton(clear_frame, text="Clear Undo History", 
                    command=lambda: messagebox.showinfo("Info", "Undo history is cleared on app restart"),
                    variant="secondary", width=150, height=32).pack(side="left")

    def _clear_recent_folders(self):
        """Clear recent folders list"""
        if messagebox.askyesno("Confirm", "Clear all recent folders?"):
            self.config.job_folder_settings.recent_folders = []
            messagebox.showinfo("Cleared", "Recent folders list cleared.")

    def _text_to_list(self, text_widget: tk.Text) -> list:
        """Convert text widget content to list"""
        content = text_widget.get("1.0", tk.END)
        return [line.strip() for line in content.split("\n") if line.strip()]

    def _on_save(self):
        """Save settings"""
        try:
            # General settings
            self.config.job_folder_settings.base_directory = self.base_dir_entry.get().strip()
            self.config.job_folder_settings.max_recent = int(self.max_recent.get())
            self.config.confirm_before_rename = self.confirm_rename.var.get()
            self.config.show_tooltips = self.show_tooltips.var.get()
            self.config.backup_before_rename = self.backup_files.var.get()
            self.config.duplicate_handling.mode = self.dup_mode.get()

            # Naming settings
            self.config.product_skus = self._text_to_list(self.skus_text)
            self.config.production_types = self._text_to_list(self.prod_types_text)
            self.config.revisions = self._text_to_list(self.revisions_text)

            # Timer settings
            self.config.timer_settings.warning_minutes = int(self.warning_mins.get())
            self.config.timer_settings.reminder_interval_minutes = int(self.reminder_mins.get())
            self.config.log_directory = self.log_dir_entry.get().strip()
            self.config.timer_settings.auto_save_log = self.auto_save_log.var.get()

            # Advanced settings
            self.config.job_folder_settings.job_number_pattern = self.job_pattern_entry.get().strip()
            self.config.duplicate_handling.auto_increment_format = self.increment_format.get().strip()

            self.result = self.config

            if self.on_save:
                self.on_save(self.config)

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Please check your input values: {e}")

    def _on_cancel(self):
        """Cancel without saving"""
        self.result = None
        self.destroy()

    def _on_reset(self):
        """Reset to default settings"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?\n\nThis cannot be undone."):
            self.config = Config()
            self.destroy()
            # Reopen with default config
            SettingsDialog(self.master, self.config, self.on_save)
