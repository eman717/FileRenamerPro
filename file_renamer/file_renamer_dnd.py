"""
File Renamer Applet for Graphic Designers - With Drag & Drop Support
Naming Convention: <Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>

Requires: pip install tkinterdnd2
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("Note: Install tkinterdnd2 for drag-and-drop support: pip install tkinterdnd2")


class FileRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Renamer - Artwork Naming Tool")
        self.root.geometry("750x650")
        self.root.resizable(True, True)

        # Store files to be renamed
        self.files_to_rename = []

        self.setup_ui()

    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # ===== Naming Convention Fields =====
        fields_frame = ttk.LabelFrame(main_frame, text="Naming Convention Fields", padding="10")
        fields_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        fields_frame.columnconfigure(1, weight=1)
        fields_frame.columnconfigure(3, weight=1)

        # Job Number
        ttk.Label(fields_frame, text="Job #:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.job_number = ttk.Entry(fields_frame, width=20)
        self.job_number.grid(row=0, column=1, sticky="ew", padx=(0, 15))

        # Product SKU
        ttk.Label(fields_frame, text="Product SKU:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.product_sku = ttk.Entry(fields_frame, width=20)
        self.product_sku.grid(row=0, column=3, sticky="ew")

        # Artwork Reference
        ttk.Label(fields_frame, text="Artwork Ref:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(10, 0))
        self.artwork_ref = ttk.Entry(fields_frame, width=20)
        self.artwork_ref.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=(10, 0))

        # Revision Number
        ttk.Label(fields_frame, text="Revision #:").grid(row=1, column=2, sticky="w", padx=(0, 5), pady=(10, 0))
        self.revision = ttk.Entry(fields_frame, width=20)
        self.revision.grid(row=1, column=3, sticky="ew", pady=(10, 0))
        self.revision.insert(0, "1")  # Default to revision 1

        # ===== File Purpose Selection =====
        purpose_frame = ttk.LabelFrame(main_frame, text="File Purpose", padding="10")
        purpose_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.file_purpose = tk.StringVar(value="PROOF")
        purposes = [
            ("PROOF", "Proof file for client approval"),
            ("PRINT", "Print-ready file"),
            ("WEB", "Web/digital use"),
            ("SOURCE", "Source/working file"),
            ("CUSTOM", "Custom purpose...")
        ]

        for i, (value, desc) in enumerate(purposes):
            rb = ttk.Radiobutton(purpose_frame, text=f"{value} - {desc}",
                                variable=self.file_purpose, value=value,
                                command=self.on_purpose_change)
            rb.grid(row=i, column=0, sticky="w")

        # Custom purpose entry (hidden by default)
        self.custom_purpose_frame = ttk.Frame(purpose_frame)
        self.custom_purpose_frame.grid(row=len(purposes), column=0, sticky="ew", pady=(5, 0))
        ttk.Label(self.custom_purpose_frame, text="Custom:").pack(side="left")
        self.custom_purpose = ttk.Entry(self.custom_purpose_frame, width=30)
        self.custom_purpose.pack(side="left", padx=(5, 0))
        self.custom_purpose_frame.grid_remove()  # Hidden initially

        # ===== File Selection / Drop Area =====
        files_frame = ttk.LabelFrame(main_frame, text="Files to Rename (Drag & Drop Here)", padding="10")
        files_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Drop zone / Listbox container
        self.drop_frame = tk.Frame(files_frame, bg="#e8f4e8", relief="groove", bd=2)
        self.drop_frame.grid(row=0, column=0, sticky="nsew")
        self.drop_frame.columnconfigure(0, weight=1)
        self.drop_frame.rowconfigure(0, weight=1)

        # Listbox with scrollbar
        list_frame = ttk.Frame(self.drop_frame)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # Setup drag and drop if available
        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
            self.drop_frame.dnd_bind('<<DragEnter>>', self.handle_drag_enter)
            self.drop_frame.dnd_bind('<<DragLeave>>', self.handle_drag_leave)

            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.handle_drop)

        # File buttons
        btn_frame = ttk.Frame(files_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ttk.Button(btn_frame, text="Add Files...", command=self.add_files).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Add Folder...", command=self.add_folder).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=self.clear_files).pack(side="left")

        # Drop hint
        dnd_status = "Drag & Drop enabled!" if HAS_DND else "Install tkinterdnd2 for drag & drop"
        drop_label = ttk.Label(files_frame, text=f"Tip: {dnd_status}",
                              foreground="green" if HAS_DND else "orange")
        drop_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        # ===== Preview Section =====
        preview_frame = ttk.LabelFrame(main_frame, text="Preview New Names", padding="10")
        preview_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Preview listbox
        preview_list_frame = ttk.Frame(preview_frame)
        preview_list_frame.grid(row=0, column=0, sticky="nsew")
        preview_list_frame.columnconfigure(0, weight=1)
        preview_list_frame.rowconfigure(0, weight=1)

        self.preview_listbox = tk.Listbox(preview_list_frame, height=6, font=("Consolas", 9))
        self.preview_listbox.grid(row=0, column=0, sticky="nsew")

        preview_scrollbar = ttk.Scrollbar(preview_list_frame, orient="vertical",
                                          command=self.preview_listbox.yview)
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_listbox.config(yscrollcommand=preview_scrollbar.set)

        ttk.Button(preview_frame, text="Update Preview", command=self.update_preview).grid(
            row=1, column=0, sticky="w", pady=(10, 0))

        # ===== Action Buttons =====
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.rename_btn = ttk.Button(action_frame, text="RENAME FILES", command=self.rename_files)
        self.rename_btn.pack(side="right", padx=(5, 0))

        ttk.Button(action_frame, text="Reset Form", command=self.reset_form).pack(side="right")

        # Example label
        example_label = ttk.Label(action_frame,
                                  text="Format: Job#_SKU_(ArtRef)_Purpose_Rev.ext",
                                  foreground="gray")
        example_label.pack(side="left")

        # Bind events for auto-preview
        for entry in [self.job_number, self.product_sku, self.artwork_ref, self.revision, self.custom_purpose]:
            entry.bind('<KeyRelease>', lambda e: self.update_preview())

    def handle_drop(self, event):
        """Handle files dropped onto the window"""
        # Parse the dropped data - tkinterdnd2 returns paths in various formats
        files_string = event.data

        # Handle different formats of dropped file paths
        files = self.parse_dropped_files(files_string)

        for f in files:
            f = f.strip()
            if os.path.isfile(f) and f not in self.files_to_rename:
                self.files_to_rename.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
            elif os.path.isdir(f):
                # If a folder is dropped, add all files from it
                for item in os.listdir(f):
                    full_path = os.path.join(f, item)
                    if os.path.isfile(full_path) and full_path not in self.files_to_rename:
                        self.files_to_rename.append(full_path)
                        self.file_listbox.insert(tk.END, os.path.basename(full_path))

        self.drop_frame.config(bg="#e8f4e8")
        self.update_preview()

    def parse_dropped_files(self, data):
        """Parse dropped file paths which may come in different formats"""
        files = []

        # Handle Windows-style paths with curly braces for paths with spaces
        if '{' in data:
            import re
            # Find all paths in curly braces
            braced = re.findall(r'\{([^}]+)\}', data)
            files.extend(braced)
            # Also get non-braced paths
            remaining = re.sub(r'\{[^}]+\}', '', data)
            files.extend(remaining.split())
        else:
            # Simple space-separated or newline-separated
            files = data.replace('\n', ' ').split()

        return [f for f in files if f.strip()]

    def handle_drag_enter(self, event):
        """Visual feedback when dragging over"""
        self.drop_frame.config(bg="#b8e8b8")

    def handle_drag_leave(self, event):
        """Reset visual when drag leaves"""
        self.drop_frame.config(bg="#e8f4e8")

    def on_purpose_change(self):
        """Handle purpose radio button change"""
        if self.file_purpose.get() == "CUSTOM":
            self.custom_purpose_frame.grid()
        else:
            self.custom_purpose_frame.grid_remove()
        self.update_preview()

    def add_files(self):
        """Open file dialog to select files"""
        files = filedialog.askopenfilenames(
            title="Select Files to Rename",
            filetypes=[
                ("All Files", "*.*"),
                ("Image Files", "*.png *.jpg *.jpeg *.tif *.tiff *.psd *.ai *.pdf"),
                ("PDF Files", "*.pdf"),
                ("Photoshop", "*.psd"),
                ("Illustrator", "*.ai"),
            ]
        )
        for f in files:
            if f not in self.files_to_rename:
                self.files_to_rename.append(f)
                self.file_listbox.insert(tk.END, os.path.basename(f))
        self.update_preview()

    def add_folder(self):
        """Open folder dialog and add all files from it"""
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            for f in os.listdir(folder):
                full_path = os.path.join(folder, f)
                if os.path.isfile(full_path) and full_path not in self.files_to_rename:
                    self.files_to_rename.append(full_path)
                    self.file_listbox.insert(tk.END, os.path.basename(full_path))
        self.update_preview()

    def remove_selected(self):
        """Remove selected files from the list"""
        selected = list(self.file_listbox.curselection())
        selected.reverse()  # Remove from end to avoid index shifting
        for idx in selected:
            self.file_listbox.delete(idx)
            del self.files_to_rename[idx]
        self.update_preview()

    def clear_files(self):
        """Clear all files from the list"""
        self.file_listbox.delete(0, tk.END)
        self.files_to_rename.clear()
        self.preview_listbox.delete(0, tk.END)

    def get_purpose(self):
        """Get the current file purpose value"""
        purpose = self.file_purpose.get()
        if purpose == "CUSTOM":
            return self.custom_purpose.get().strip().upper() or "CUSTOM"
        return purpose

    def generate_new_name(self, original_path, index=0):
        """Generate new filename based on convention"""
        # Get the file extension
        _, ext = os.path.splitext(original_path)

        # Get field values
        job = self.job_number.get().strip()
        sku = self.product_sku.get().strip()
        art_ref = self.artwork_ref.get().strip()
        purpose = self.get_purpose()
        rev = self.revision.get().strip()

        # Build the new name
        # Format: <Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>
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
            return os.path.basename(original_path)  # Return original if no fields filled

        new_name = "_".join(parts) + ext
        return new_name

    def update_preview(self, event=None):
        """Update the preview listbox with new names"""
        self.preview_listbox.delete(0, tk.END)

        for i, filepath in enumerate(self.files_to_rename):
            original = os.path.basename(filepath)
            new_name = self.generate_new_name(filepath, i)
            self.preview_listbox.insert(tk.END, f"{original}  -->  {new_name}")

    def rename_files(self):
        """Perform the actual file renaming"""
        if not self.files_to_rename:
            messagebox.showwarning("No Files", "Please add files to rename first.")
            return

        # Validate required fields
        if not self.job_number.get().strip():
            messagebox.showwarning("Missing Field", "Please enter a Job Number.")
            return

        # Confirm with user
        count = len(self.files_to_rename)
        if not messagebox.askyesno("Confirm Rename",
                                   f"Are you sure you want to rename {count} file(s)?"):
            return

        # Perform renaming
        renamed = 0
        errors = []

        for filepath in self.files_to_rename[:]:  # Copy list to avoid modification during iteration
            try:
                directory = os.path.dirname(filepath)
                new_name = self.generate_new_name(filepath)
                new_path = os.path.join(directory, new_name)

                # Check if target already exists
                if os.path.exists(new_path) and filepath != new_path:
                    errors.append(f"{os.path.basename(filepath)}: Target file already exists")
                    continue

                os.rename(filepath, new_path)
                renamed += 1

            except Exception as e:
                errors.append(f"{os.path.basename(filepath)}: {str(e)}")

        # Show results
        if errors:
            error_msg = "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more errors"
            messagebox.showwarning("Rename Complete with Errors",
                                  f"Renamed {renamed} file(s).\n\nErrors:\n{error_msg}")
        else:
            messagebox.showinfo("Success", f"Successfully renamed {renamed} file(s)!")

        # Clear the file list after successful rename
        self.clear_files()

    def reset_form(self):
        """Reset all form fields"""
        self.job_number.delete(0, tk.END)
        self.product_sku.delete(0, tk.END)
        self.artwork_ref.delete(0, tk.END)
        self.revision.delete(0, tk.END)
        self.revision.insert(0, "1")
        self.custom_purpose.delete(0, tk.END)
        self.file_purpose.set("PROOF")
        self.custom_purpose_frame.grid_remove()
        self.clear_files()


def main():
    # Use TkinterDnD if available, otherwise regular Tk
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    # Try to set a modern theme
    try:
        style = ttk.Style()
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        elif 'clam' in style.theme_names():
            style.theme_use('clam')
    except:
        pass

    app = FileRenamerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
