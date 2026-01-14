"""
Services for File Renamer Pro
Business logic for file operations, undo/redo, etc.
"""

import os
import shutil
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from enum import Enum

from .utils import sanitize_filename, get_unique_path, ensure_directory

logger = logging.getLogger(__name__)


class FileOperation(Enum):
    """Types of file operations"""
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"


@dataclass
class RenameRecord:
    """Record of a single file rename operation"""
    original_path: str
    new_path: str
    operation: FileOperation
    timestamp: str
    success: bool = True
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_path': self.original_path,
            'new_path': self.new_path,
            'operation': self.operation.value,
            'timestamp': self.timestamp,
            'success': self.success,
            'error': self.error,
        }


@dataclass
class RenameSession:
    """A batch of rename operations that can be undone together"""
    id: str
    records: List[RenameRecord] = field(default_factory=list)
    timestamp: str = ""
    job_number: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.records if r.success)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.records if not r.success)


class UndoManager:
    """Manages undo/redo operations for file renames"""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._undo_stack: List[RenameSession] = []
        self._redo_stack: List[RenameSession] = []
        self._lock = threading.Lock()

    def record_session(self, session: RenameSession) -> None:
        """Record a rename session for potential undo"""
        with self._lock:
            self._undo_stack.append(session)
            # Clear redo stack when new action is performed
            self._redo_stack.clear()
            # Trim history if needed
            while len(self._undo_stack) > self.max_history:
                self._undo_stack.pop(0)
            logger.info(f"Recorded session {session.id} with {len(session.records)} operations")

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self._redo_stack) > 0

    def undo(self) -> tuple[bool, str, int]:
        """
        Undo the last rename session.
        
        Returns:
            Tuple of (success, message, files_restored)
        """
        with self._lock:
            if not self._undo_stack:
                return False, "Nothing to undo", 0

            session = self._undo_stack.pop()
            restored = 0
            errors = []

            # Process in reverse order
            for record in reversed(session.records):
                if not record.success:
                    continue  # Skip failed operations

                try:
                    if Path(record.new_path).exists():
                        if record.operation == FileOperation.MOVE:
                            # Move back to original location
                            original_dir = Path(record.original_path).parent
                            ensure_directory(original_dir)
                            shutil.move(record.new_path, record.original_path)
                        elif record.operation == FileOperation.COPY:
                            # Delete the copy
                            os.remove(record.new_path)
                        restored += 1
                    else:
                        errors.append(f"File not found: {record.new_path}")
                except Exception as e:
                    errors.append(f"{Path(record.new_path).name}: {str(e)}")
                    logger.error(f"Undo failed for {record.new_path}: {e}")

            # Add to redo stack
            self._redo_stack.append(session)

            if errors:
                return False, f"Restored {restored} files with {len(errors)} errors", restored
            return True, f"Restored {restored} files", restored

    def redo(self) -> tuple[bool, str, int]:
        """
        Redo the last undone session.
        
        Returns:
            Tuple of (success, message, files_renamed)
        """
        with self._lock:
            if not self._redo_stack:
                return False, "Nothing to redo", 0

            session = self._redo_stack.pop()
            renamed = 0
            errors = []

            for record in session.records:
                if not record.success:
                    continue

                try:
                    if Path(record.original_path).exists():
                        dest_dir = Path(record.new_path).parent
                        ensure_directory(dest_dir)
                        if record.operation == FileOperation.MOVE:
                            shutil.move(record.original_path, record.new_path)
                        elif record.operation == FileOperation.COPY:
                            shutil.copy2(record.original_path, record.new_path)
                        renamed += 1
                    else:
                        errors.append(f"File not found: {record.original_path}")
                except Exception as e:
                    errors.append(str(e))

            # Add back to undo stack
            self._undo_stack.append(session)

            if errors:
                return False, f"Renamed {renamed} files with {len(errors)} errors", renamed
            return True, f"Renamed {renamed} files", renamed

    def get_undo_description(self) -> str:
        """Get description of what will be undone"""
        if not self._undo_stack:
            return ""
        session = self._undo_stack[-1]
        return f"Undo {session.success_count} file(s) from Job #{session.job_number}"

    def get_redo_description(self) -> str:
        """Get description of what will be redone"""
        if not self._redo_stack:
            return ""
        session = self._redo_stack[-1]
        return f"Redo {session.success_count} file(s) for Job #{session.job_number}"

    def clear_history(self) -> None:
        """Clear all undo/redo history"""
        with self._lock:
            self._undo_stack.clear()
            self._redo_stack.clear()


class RenameService:
    """Service for handling file rename operations"""

    def __init__(self, undo_manager: Optional[UndoManager] = None):
        self.undo_manager = undo_manager or UndoManager()
        self._lock = threading.Lock()

    def generate_filename(self, original_path: str, job_number: str, sku: str,
                         artwork_ref: str, purpose: str, revision: str) -> str:
        """
        Generate a new filename following the naming convention.
        
        Convention: <Job#>_<ProductSKU>_(<ArtworkReference>)_<FilePurpose>_<revision#>.<filetype>
        
        Args:
            original_path: Original file path (to get extension)
            job_number: Job number
            sku: Product SKU
            artwork_ref: Artwork reference/description
            purpose: File purpose (SOURCE, PROOF, PRINT, etc.)
            revision: Revision number or FINAL
            
        Returns:
            Generated filename
        """
        _, ext = os.path.splitext(original_path)
        ext = ext.lower()

        parts = []
        if job_number:
            parts.append(sanitize_filename(job_number))
        if sku:
            parts.append(sanitize_filename(sku))
        if artwork_ref:
            # Wrap in parentheses
            sanitized_ref = sanitize_filename(artwork_ref)
            parts.append(f"({sanitized_ref})")
        if purpose:
            parts.append(sanitize_filename(purpose))
        if revision:
            parts.append(sanitize_filename(revision))

        if not parts:
            return os.path.basename(original_path)

        return "_".join(parts) + ext

    def rename_files(self, files: List[dict], dest_folder: str, job_number: str,
                    on_progress: Optional[Callable[[int, int, str], None]] = None,
                    duplicate_mode: str = "skip") -> RenameSession:
        """
        Rename and move a batch of files.
        
        Args:
            files: List of dicts with 'path', 'new_name' keys
            dest_folder: Destination folder path
            job_number: Job number for logging
            on_progress: Callback for progress updates (current, total, filename)
            duplicate_mode: How to handle duplicates: skip, increment, overwrite
            
        Returns:
            RenameSession with results
        """
        session = RenameSession(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            job_number=job_number,
        )

        ensure_directory(Path(dest_folder))
        total = len(files)

        for i, file_info in enumerate(files):
            original_path = file_info['path']
            new_name = file_info['new_name']
            new_path = os.path.join(dest_folder, new_name)

            if on_progress:
                on_progress(i + 1, total, new_name)

            record = RenameRecord(
                original_path=original_path,
                new_path=new_path,
                operation=FileOperation.MOVE,
                timestamp=datetime.now().isoformat(),
            )

            try:
                # Handle duplicates
                if os.path.exists(new_path):
                    if duplicate_mode == "skip":
                        record.success = False
                        record.error = "File already exists"
                        session.records.append(record)
                        continue
                    elif duplicate_mode == "increment":
                        new_path = str(get_unique_path(Path(new_path)))
                        record.new_path = new_path
                    elif duplicate_mode == "overwrite":
                        os.remove(new_path)

                # Perform the move
                shutil.move(original_path, new_path)
                record.success = True
                logger.info(f"Renamed: {original_path} -> {new_path}")

            except PermissionError as e:
                record.success = False
                record.error = "Permission denied"
                logger.error(f"Permission denied: {original_path}: {e}")
            except FileNotFoundError as e:
                record.success = False
                record.error = "Source file not found"
                logger.error(f"File not found: {original_path}: {e}")
            except Exception as e:
                record.success = False
                record.error = str(e)
                logger.error(f"Error renaming {original_path}: {e}")

            session.records.append(record)

        # Record for undo
        if session.success_count > 0:
            self.undo_manager.record_session(session)

        return session

    def rename_files_async(self, files: List[dict], dest_folder: str, job_number: str,
                          on_progress: Optional[Callable[[int, int, str], None]] = None,
                          on_complete: Optional[Callable[[RenameSession], None]] = None,
                          duplicate_mode: str = "skip") -> threading.Thread:
        """
        Rename files in a background thread.
        
        Returns:
            The thread object (already started)
        """
        def worker():
            session = self.rename_files(files, dest_folder, job_number, 
                                       on_progress, duplicate_mode)
            if on_complete:
                on_complete(session)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def validate_files(self, files: List[str]) -> List[tuple[str, bool, str]]:
        """
        Validate a list of files before renaming.
        
        Returns:
            List of (path, is_valid, error_message) tuples
        """
        results = []
        for path in files:
            if not os.path.exists(path):
                results.append((path, False, "File not found"))
            elif not os.path.isfile(path):
                results.append((path, False, "Not a file"))
            elif not os.access(path, os.R_OK):
                results.append((path, False, "File not readable"))
            else:
                results.append((path, True, ""))
        return results
