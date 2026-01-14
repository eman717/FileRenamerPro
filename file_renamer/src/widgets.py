"""
Custom Widgets for File Renamer Pro
Styled UI components with the Creative Studio theme
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Optional, List

from .theme import Theme
from .utils import parse_dropped_files

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = None


class StyledButton(tk.Canvas):
    """Custom styled button with hover effects"""

    def __init__(self, parent, text: str, command: Optional[Callable] = None, 
                 variant: str = "primary", width: int = 120, height: int = 36, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.variant = variant
        self._width = width
        self._height = height
        self._enabled = True
        self._tooltip_text = ""
        self._tooltip_window = None

        self.colors = {
            "primary": {
                "bg": Theme.ACCENT_PRIMARY, 
                "bg_hover": "#ff8555", 
                "fg": Theme.TEXT_ON_ACCENT,
                "bg_disabled": Theme.BG_TERTIARY, 
                "fg_disabled": Theme.TEXT_TERTIARY
            },
            "secondary": {
                "bg": Theme.BG_TERTIARY, 
                "bg_hover": Theme.BG_ELEVATED, 
                "fg": Theme.TEXT_PRIMARY,
                "bg_disabled": Theme.BG_SECONDARY, 
                "fg_disabled": Theme.TEXT_TERTIARY
            },
            "success": {
                "bg": Theme.ACCENT_SUCCESS, 
                "bg_hover": "#55c774", 
                "fg": Theme.TEXT_ON_ACCENT,
                "bg_disabled": Theme.BG_TERTIARY, 
                "fg_disabled": Theme.TEXT_TERTIARY
            },
            "danger": {
                "bg": Theme.ACCENT_DANGER, 
                "bg_hover": "#ff5f6d", 
                "fg": Theme.TEXT_ON_ACCENT,
                "bg_disabled": Theme.BG_TERTIARY, 
                "fg_disabled": Theme.TEXT_TERTIARY
            }
        }

        try:
            self.configure(bg=parent.cget('bg'))
        except:
            self.configure(bg=Theme.BG_PRIMARY)
            
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, hover: bool = False):
        self.delete("all")
        colors = self.colors.get(self.variant, self.colors["primary"])
        
        if not self._enabled:
            bg, fg = colors["bg_disabled"], colors["fg_disabled"]
        else:
            bg = colors["bg_hover"] if hover else colors["bg"]
            fg = colors["fg"]
        
        # Draw rounded rectangle
        r = 6
        points = [
            2+r, 2, self._width-2-r, 2, self._width-2, 2, self._width-2, 2+r,
            self._width-2, self._height-2-r, self._width-2, self._height-2,
            self._width-2-r, self._height-2, 2+r, self._height-2,
            2, self._height-2, 2, self._height-2-r, 2, 2+r, 2, 2
        ]
        self.create_polygon(points, smooth=True, fill=bg, outline="")
        self.create_text(self._width // 2, self._height // 2, text=self.text, 
                        fill=fg, font=Theme.FONT_BUTTON)

    def _on_enter(self, e):
        if self._enabled:
            self._draw(hover=True)
            self.config(cursor="hand2")
        self._show_tooltip()

    def _on_leave(self, e):
        self._draw(hover=False)
        self.config(cursor="")
        self._hide_tooltip()

    def _on_click(self, e):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self._draw()

    def set_tooltip(self, text: str):
        self._tooltip_text = text

    def _show_tooltip(self):
        if not self._tooltip_text:
            return
        x, y, _, _ = self.bbox("all") if self.bbox("all") else (0, 0, 0, 0)
        x += self.winfo_rootx() + 25
        y += self.winfo_rooty() + 25
        
        self._tooltip_window = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self._tooltip_text, justify='left',
                        background=Theme.BG_ELEVATED, foreground=Theme.TEXT_PRIMARY,
                        relief='solid', borderwidth=1, font=Theme.FONT_SMALL,
                        padx=6, pady=3)
        label.pack()

    def _hide_tooltip(self):
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None


class SectionCard(tk.Frame):
    """A styled card container with title"""

    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)
        self.configure(highlightbackground=Theme.BORDER_SUBTLE, highlightthickness=1)

        if title:
            title_frame = tk.Frame(self, bg=Theme.BG_SECONDARY)
            title_frame.pack(fill="x", padx=Theme.PAD_MD, pady=(Theme.PAD_MD, Theme.PAD_SM))
            tk.Label(title_frame, text=title.upper(), font=Theme.FONT_SECTION,
                    fg=Theme.TEXT_SECONDARY, bg=Theme.BG_SECONDARY).pack(side="left")
            tk.Frame(self, bg=Theme.ACCENT_PRIMARY, height=2).pack(fill="x", padx=Theme.PAD_MD)

        self.content = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.content.pack(fill="both", expand=True, padx=Theme.PAD_MD, pady=Theme.PAD_MD)


class DropZone(tk.Frame):
    """A styled drop zone for files with drag-and-drop support"""

    def __init__(self, parent, title: str, subtitle: str, color: str, 
                 icon_text: str = "", **kwargs):
        super().__init__(parent, bg=color, highlightbackground=Theme.BORDER_DEFAULT,
                        highlightthickness=2, **kwargs)

        self.base_color = color
        self.files: List[str] = []
        self.on_files_changed: Optional[Callable[[], None]] = None

        # Content
        content = tk.Frame(self, bg=color)
        content.pack(fill="both", expand=True, padx=Theme.PAD_SM, pady=Theme.PAD_SM)

        # Header
        header = tk.Frame(content, bg=color)
        header.pack(fill="x")

        if icon_text:
            tk.Label(header, text=icon_text, font=("Segoe UI", 14), 
                    fg=Theme.TEXT_PRIMARY, bg=color).pack(side="left")

        tk.Label(header, text=title, font=("Segoe UI Semibold", 11), 
                fg=Theme.TEXT_PRIMARY, bg=color).pack(side="left", padx=(Theme.PAD_XS, 0))

        # Clear button
        self.clear_btn = tk.Label(header, text="x", font=("Segoe UI", 10), 
                                  fg=Theme.TEXT_TERTIARY, bg=color, cursor="hand2")
        self.clear_btn.pack(side="right")
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_files())

        # Subtitle
        tk.Label(content, text=subtitle, font=Theme.FONT_SMALL, 
                fg=Theme.TEXT_TERTIARY, bg=color).pack(anchor="w")

        # File list
        self.file_frame = tk.Frame(content, bg=color)
        self.file_frame.pack(fill="both", expand=True, pady=(Theme.PAD_SM, 0))

        # Placeholder
        self.placeholder = tk.Label(self.file_frame, text="Drop files here", 
                                    font=Theme.FONT_BODY, fg=Theme.TEXT_TERTIARY, bg=color)
        self.placeholder.pack(expand=True)

        # File listbox (hidden initially)
        self.listbox = tk.Listbox(self.file_frame, bg=color, fg=Theme.TEXT_PRIMARY,
                                  selectbackground=Theme.ACCENT_PRIMARY, highlightthickness=0,
                                  borderwidth=0, font=Theme.FONT_MONO, height=3)

        # Setup DnD if available
        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind('<<Drop>>', self._handle_drop)
                self.dnd_bind('<<DragEnter>>', lambda e: self.config(highlightbackground=Theme.ACCENT_PRIMARY))
                self.dnd_bind('<<DragLeave>>', lambda e: self.config(highlightbackground=Theme.BORDER_DEFAULT))
            except Exception:
                pass  # DnD not available for this widget

    def _handle_drop(self, event):
        self.config(highlightbackground=Theme.BORDER_DEFAULT)
        files = parse_dropped_files(event.data)
        for f in files:
            if os.path.isfile(f) and f not in self.files:
                self.files.append(f)
        self._update_display()
        if self.on_files_changed:
            self.on_files_changed()

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

    def get_files(self) -> List[str]:
        return self.files.copy()

    def has_files(self) -> bool:
        return len(self.files) > 0

    def remove_file(self, index: int):
        if 0 <= index < len(self.files):
            self.files.pop(index)
            self._update_display()
            if self.on_files_changed:
                self.on_files_changed()


class StyledEntry(tk.Entry):
    """Custom styled entry with placeholder support"""

    def __init__(self, parent, placeholder: str = "", **kwargs):
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

    def get_value(self) -> str:
        """Get the actual value (not placeholder)"""
        if self._has_placeholder:
            return ""
        return self.get().strip()


class StatusBar(tk.Frame):
    """Status bar for displaying messages"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.BG_TERTIARY, **kwargs)
        
        self.message_label = tk.Label(self, text="Ready", font=Theme.FONT_SMALL,
                                      fg=Theme.TEXT_SECONDARY, bg=Theme.BG_TERTIARY,
                                      anchor="w")
        self.message_label.pack(side="left", fill="x", expand=True, padx=Theme.PAD_SM, pady=2)
        
        self.info_label = tk.Label(self, text="", font=Theme.FONT_SMALL,
                                   fg=Theme.TEXT_TERTIARY, bg=Theme.BG_TERTIARY,
                                   anchor="e")
        self.info_label.pack(side="right", padx=Theme.PAD_SM, pady=2)

    def set_message(self, message: str, message_type: str = "info"):
        colors = {
            "info": Theme.TEXT_SECONDARY,
            "success": Theme.ACCENT_SUCCESS,
            "warning": Theme.ACCENT_WARNING,
            "error": Theme.ACCENT_DANGER,
        }
        self.message_label.config(text=message, fg=colors.get(message_type, Theme.TEXT_SECONDARY))

    def set_info(self, info: str):
        self.info_label.config(text=info)

    def clear(self):
        self.message_label.config(text="Ready", fg=Theme.TEXT_SECONDARY)
        self.info_label.config(text="")


class Tooltip:
    """Tooltip helper class"""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background=Theme.BG_ELEVATED, foreground=Theme.TEXT_PRIMARY,
                        relief='solid', borderwidth=1, font=Theme.FONT_SMALL,
                        padx=6, pady=3)
        label.pack()

    def _hide(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class ScrollableFrame(tk.Frame):
    """A scrollable frame container"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(self, bg=Theme.BG_PRIMARY, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=Theme.BG_PRIMARY)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # Make frame expand with canvas
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        # Windows/macOS
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
