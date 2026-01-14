"""
Job Folder Parser for File Renamer Pro
Extracts job information from folder names
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class JobInfo:
    """Structured job information"""
    job_number: str = ""
    customer: str = ""
    company: str = ""
    sku: str = ""
    quantity: str = ""
    po_number: str = ""
    raw: str = ""

    def is_valid(self) -> bool:
        """Check if minimum required fields are present"""
        return bool(self.job_number)

    def get(self, key: str, default: str = "") -> str:
        """Dictionary-like access for backwards compatibility"""
        return getattr(self, key, default) or default


class JobFolderParser:
    """Parses job folder names to extract components"""

    # Common patterns for job folder names
    PATTERNS = [
        # Pattern 1: Job#_CustomerName_Company_SKU x Qty_(PO#)
        r'^(\d+)_([^_]+)_([^_]+)_(.+?)\s*[xX]\s*(\d+)_?\(?([^)]*)\)?$',
        # Pattern 2: Job#_CustomerName_Company_SKU_(PO#)
        r'^(\d+)_([^_]+)_([^_]+)_([^_]+)_?\(?([^)]*)\)?$',
        # Pattern 3: Job#_CustomerName_SKU
        r'^(\d+)_([^_]+)_(.+)$',
        # Pattern 4: Job# - Customer Name
        r'^(\d+)\s*[-_]\s*(.+)$',
    ]

    @classmethod
    def parse(cls, folder_name: str) -> JobInfo:
        """
        Parse folder name to extract job components.
        
        Supports multiple formats:
        - 12345_JohnDoe_AcmeCorp_MUG-11OZ x 100_(PO-98765)
        - 12345_JohnDoe_AcmeCorp_MUG-11OZ_(PO-98765)
        - 12345_JohnDoe_MUG-11OZ
        - 12345 - John Doe Project
        
        Returns:
            JobInfo dataclass with extracted components
        """
        if not folder_name:
            logger.debug("Empty folder name provided")
            return JobInfo(raw="")

        result = JobInfo(raw=folder_name)
        folder_name = folder_name.strip()

        # Try to extract PO number from end (in parentheses or brackets)
        po_match = re.search(r'[\(\[]([^\)\]]+)[\)\]]$', folder_name)
        if po_match:
            result.po_number = po_match.group(1).strip()
            folder_name = folder_name[:po_match.start()].strip('_- ')

        # Split by underscores
        parts = folder_name.split('_')

        if len(parts) >= 1:
            # First part should contain job number
            job_match = re.match(r'^(\d+)', parts[0])
            if job_match:
                result.job_number = job_match.group(1)
            else:
                logger.warning(f"Could not extract job number from: {parts[0]}")

        if len(parts) >= 2:
            result.customer = cls._clean_name(parts[1])

        if len(parts) >= 3:
            result.company = cls._clean_name(parts[2])

        if len(parts) >= 4:
            # SKU x Quantity format
            sku_qty = '_'.join(parts[3:])  # Join remaining parts
            sku_match = re.match(r'(.+?)\s*[xX]\s*(\d+)', sku_qty)
            if sku_match:
                result.sku = sku_match.group(1).strip()
                result.quantity = sku_match.group(2)
            else:
                result.sku = sku_qty.strip()

        logger.debug(f"Parsed '{result.raw}' -> job={result.job_number}, "
                    f"customer={result.customer}, sku={result.sku}")
        return result

    @staticmethod
    def _clean_name(name: str) -> str:
        """Clean up a name component"""
        # Remove common prefixes/suffixes
        name = name.strip('_- ')
        # Convert camelCase to spaces if needed
        # name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return name

    @classmethod
    def validate_folder_name(cls, folder_name: str) -> tuple[bool, str]:
        """
        Validate a folder name format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not folder_name:
            return False, "Folder name is empty"

        info = cls.parse(folder_name)
        
        if not info.job_number:
            return False, "Could not extract job number"
        
        if not info.job_number.isdigit():
            return False, "Job number must be numeric"

        return True, ""

    @classmethod
    def suggest_folder_name(cls, job_number: str, customer: str, 
                           company: str = "", sku: str = "", 
                           quantity: str = "", po_number: str = "") -> str:
        """Generate a properly formatted folder name"""
        parts = [job_number]
        
        if customer:
            parts.append(customer.replace(' ', ''))
        
        if company:
            parts.append(company.replace(' ', ''))
        
        if sku:
            if quantity:
                parts.append(f"{sku} x {quantity}")
            else:
                parts.append(sku)
        
        result = '_'.join(parts)
        
        if po_number:
            result += f"_({po_number})"
        
        return result
