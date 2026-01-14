"""
Revision Detection for File Renamer Pro
Handles automatic revision number detection and management
"""

import os
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class RevisionDetector:
    """Handles automatic revision detection based on existing files"""

    # Common design file extensions to check
    DESIGN_EXTENSIONS = [".psd", ".ai", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".eps", ".svg"]

    def __init__(self, revision_list: List[str]):
        """
        Initialize revision detector.
        
        Args:
            revision_list: List of valid revision values (e.g., ["1", "2", "3", "4", "5", "FINAL"])
        """
        self.revision_list = revision_list or ["1", "2", "3", "4", "5", "FINAL"]

    def find_next_revision(self, folder_path: str, base_pattern: str, 
                          extension: str = ".psd") -> str:
        """
        Find the next revision number based on existing files.
        
        Args:
            folder_path: Path to search for existing files
            base_pattern: Base filename pattern (e.g., "12345_MUG-11OZ_(BlueDog)_SOURCE")
            extension: File extension to check
            
        Returns:
            Next revision number as string
        """
        if not folder_path or not os.path.isdir(folder_path):
            logger.debug(f"Invalid folder path: {folder_path}")
            return self._get_first_revision()

        if not base_pattern:
            return self._get_first_revision()

        found_revisions = self._scan_for_revisions(folder_path, base_pattern, extension)

        if not found_revisions:
            return self._get_first_revision()

        return self._calculate_next_revision(found_revisions)

    def get_existing_revisions(self, folder_path: str, base_pattern: str, 
                               extension: Optional[str] = None) -> List[str]:
        """
        Get list of existing revision numbers for a pattern.
        
        Args:
            folder_path: Path to search
            base_pattern: Base filename pattern
            extension: Specific extension to check, or None to check all design extensions
            
        Returns:
            Sorted list of found revision numbers
        """
        if not folder_path or not os.path.isdir(folder_path):
            return []

        if not base_pattern:
            return []

        extensions = [extension] if extension else self.DESIGN_EXTENSIONS
        all_found: set = set()

        for ext in extensions:
            found = self._scan_for_revisions(folder_path, base_pattern, ext)
            all_found.update(found)

        # Sort: numeric first (ascending), then FINAL
        return sorted(all_found, key=lambda x: (x == "FINAL", int(x) if x.isdigit() else 999))

    def _scan_for_revisions(self, folder_path: str, base_pattern: str, 
                           extension: str) -> List[str]:
        """Scan folder for files matching pattern and extract revisions"""
        escaped_base = re.escape(base_pattern)
        # Match: base_pattern_revision.extension
        pattern = re.compile(
            rf"^{escaped_base}_(\d+|FINAL){re.escape(extension)}$", 
            re.IGNORECASE
        )

        found_revisions = []
        try:
            for filename in os.listdir(folder_path):
                match = pattern.match(filename)
                if match:
                    rev = match.group(1).upper()
                    found_revisions.append("FINAL" if rev == "FINAL" else rev)
                    logger.debug(f"Found existing revision: {filename} -> {rev}")
        except PermissionError as e:
            logger.error(f"Permission denied accessing {folder_path}: {e}")
        except OSError as e:
            logger.error(f"Error scanning directory {folder_path}: {e}")

        return found_revisions

    def _get_first_revision(self) -> str:
        """Get the first revision from the list"""
        return self.revision_list[0] if self.revision_list else "1"

    def _calculate_next_revision(self, found_revisions: List[str]) -> str:
        """Calculate the next revision based on found ones"""
        # Find max numeric revision
        max_numeric = 0
        has_final = False

        for rev in found_revisions:
            if rev == "FINAL":
                has_final = True
            else:
                try:
                    num = int(rev)
                    if num > max_numeric:
                        max_numeric = num
                except ValueError:
                    pass

        # If FINAL exists, suggest FINAL again (or ask user)
        if has_final:
            logger.info("FINAL revision exists - suggesting FINAL")
            return "FINAL"

        next_rev = str(max_numeric + 1)

        # Check if next revision is in our list
        if next_rev in self.revision_list:
            return next_rev

        # If we've exceeded the numeric revisions, suggest FINAL
        if "FINAL" in self.revision_list and max_numeric >= 5:
            return "FINAL"

        # Otherwise return the calculated next
        return next_rev

    def is_valid_revision(self, revision: str) -> bool:
        """Check if a revision value is valid"""
        return revision in self.revision_list or revision.isdigit()

    def parse_revision_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract revision number from a filename.
        
        Args:
            filename: Full filename to parse
            
        Returns:
            Revision string if found, None otherwise
        """
        # Pattern: anything_REVISION.ext where REVISION is number or FINAL
        match = re.search(r'_(\d+|FINAL)\.[^.]+$', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper() if match.group(1).upper() == "FINAL" else match.group(1)
        return None
