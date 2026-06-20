"""
Job Folder Parser for File Renamer Pro
Extracts job information from folder names
"""

import re
import logging
from dataclasses import dataclass
from datetime import datetime
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
    # Date-based jobs: job_number is a compact date with a daily sequence
    # (e.g. "20260620-1"). job_date is the derived calendar date; date_sequence
    # is the per-day counter ("1", "2", ...). date_source records where the
    # date came from: "name" (parsed from the folder name) or "" (not in name;
    # the app fills in "metadata" from the folder's created date as a fallback).
    job_date: str = ""
    date_sequence: str = ""
    date_source: str = ""

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

        # Format A (current production structure), space/parenthesis delimited:
        #   J<YYYYMMDD>-<seq> (Customer @ Company) <SKU / job reference>
        # e.g. "J20260603-1 (Janelle Nelson @ Her Request) KC Royals branding"
        # The trailing text is the intended SKU for the job. The artwork
        # reference is NOT stored in the folder name (it is entered per file for
        # the filename), so it is not parsed here. Quantity is not used.
        m = re.match(r'^(J?\d{8}(?:-\d+)?)\s*\(([^)]*)\)\s*(.*)$',
                     folder_name, re.IGNORECASE)
        if m:
            result.job_number = m.group(1).strip()
            date_token = cls._parse_date_token(m.group(1))
            if date_token:
                result.job_date, result.date_sequence = date_token
                result.date_source = "name"
            inside = m.group(2).strip()
            if '@' in inside:
                customer, company = inside.split('@', 1)
                result.customer = customer.strip()
                result.company = company.strip()
            else:
                result.customer = inside

            # Trailing text holds the SKU, optionally with a "x<qty>" quantity
            # and a trailing PO marker in [...] or (...).
            # e.g. "Pro_SimpleRTK_GNSS_Case x3 [PO# NotYet]"
            trailing = m.group(3).strip()
            po_match = re.search(r'[\(\[]([^)\]]*)[\)\]]\s*$', trailing)
            if po_match:
                # Drop a redundant "PO#"/"PO #" prefix (e.g. "PO# NotYet" -> "NotYet")
                po_value = re.sub(r'^PO\s*#\s*', '', po_match.group(1).strip(),
                                  flags=re.IGNORECASE).strip()
                result.po_number = po_value
                trailing = trailing[:po_match.start()].strip()
            # Quantity ordered, written compactly as " x<n>" at the end
            qty_match = re.search(r'\s+[xX]\s*(\d+)\s*$', trailing)
            if qty_match:
                result.quantity = qty_match.group(1)
                trailing = trailing[:qty_match.start()].strip()
            result.sku = trailing

            logger.debug(f"Parsed (Format A) '{result.raw}' -> "
                         f"job={result.job_number}, customer={result.customer}, "
                         f"company={result.company}, sku={result.sku}, "
                         f"qty={result.quantity}, po={result.po_number}")
            return result

        # Try to extract PO number from end (in parentheses or brackets)
        po_match = re.search(r'[\(\[]([^\)\]]+)[\)\]]$', folder_name)
        if po_match:
            result.po_number = po_match.group(1).strip()
            folder_name = folder_name[:po_match.start()].strip('_- ')

        # Split by underscores
        parts = folder_name.split('_')

        if len(parts) >= 1:
            # First part is the job number. New folder structure uses a compact
            # date with a daily sequence (e.g. "20260620-1") as the unique job
            # number; the older structure uses a plain count (e.g. "12345").
            date_token = cls._parse_date_token(parts[0])
            if date_token:
                # Keep the whole token (incl. the "-N" suffix) as the job number
                result.job_number = parts[0].strip()
                result.job_date, result.date_sequence = date_token
                result.date_source = "name"
            else:
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
    def _parse_date_token(token: str):
        """
        Detect a compact-date job id: YYYYMMDD optionally followed by "-N".

        Returns:
            Tuple of (date_str "YYYY-MM-DD", sequence_str) if the token is a
            valid calendar date in that form, otherwise None. The sequence is
            "" when no "-N" suffix is present.
        """
        if not token:
            return None
        m = re.match(r'^J?(\d{8})(?:-(\d+))?$', token.strip(), re.IGNORECASE)
        if not m:
            return None
        try:
            dt = datetime.strptime(m.group(1), '%Y%m%d')
        except ValueError:
            # 8 digits but not a real date (e.g. a plain 8-digit count)
            return None
        return dt.strftime('%Y-%m-%d'), (m.group(2) or "")

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

        # Accept a plain numeric count (old structure) or a compact-date job id
        # like YYYYMMDD-N / JYYYYMMDD-N (new structure).
        if not (info.job_number.isdigit()
                or re.match(r'^J?\d{8}(-\d+)?$', info.job_number, re.IGNORECASE)):
            return False, "Job number must be numeric or a date (J?YYYYMMDD[-N])"

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
