"""Tests for JobFolderParser"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.job_parser import JobFolderParser, JobInfo


class TestJobFolderParser:
    """Tests for JobFolderParser class"""

    def test_parse_full_format(self):
        """Test parsing full folder name format"""
        folder = "12345_JohnDoe_AcmeCorp_MUG-11OZ x 100_(PO-98765)"
        result = JobFolderParser.parse(folder)
        
        assert result.job_number == "12345"
        assert result.customer == "JohnDoe"
        assert result.company == "AcmeCorp"
        assert result.sku == "MUG-11OZ"
        assert result.quantity == "100"
        assert result.po_number == "PO-98765"

    def test_parse_without_po(self):
        """Test parsing without PO number"""
        folder = "12345_JohnDoe_AcmeCorp_MUG-11OZ x 100"
        result = JobFolderParser.parse(folder)
        
        assert result.job_number == "12345"
        assert result.customer == "JohnDoe"
        assert result.company == "AcmeCorp"
        assert result.sku == "MUG-11OZ"
        assert result.quantity == "100"
        assert result.po_number == ""

    def test_parse_without_quantity(self):
        """Test parsing without quantity"""
        folder = "12345_JohnDoe_AcmeCorp_MUG-11OZ_(PO-98765)"
        result = JobFolderParser.parse(folder)
        
        assert result.job_number == "12345"
        assert result.customer == "JohnDoe"
        assert result.sku == "MUG-11OZ"
        assert result.po_number == "PO-98765"

    def test_parse_minimal_format(self):
        """Test parsing minimal format"""
        folder = "12345_JohnDoe"
        result = JobFolderParser.parse(folder)
        
        assert result.job_number == "12345"
        assert result.customer == "JohnDoe"
        assert result.company == ""
        assert result.sku == ""

    def test_parse_job_number_only(self):
        """Test parsing job number only"""
        folder = "12345"
        result = JobFolderParser.parse(folder)
        
        assert result.job_number == "12345"
        assert result.customer == ""

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = JobFolderParser.parse("")
        
        assert result.job_number == ""
        assert result.is_valid() == False

    def test_parse_with_brackets_po(self):
        """Test parsing with square brackets for PO"""
        folder = "12345_JohnDoe_AcmeCorp_MUG-11OZ x 100_[PO-98765]"
        result = JobFolderParser.parse(folder)
        
        assert result.po_number == "PO-98765"

    def test_is_valid(self):
        """Test is_valid method"""
        valid = JobFolderParser.parse("12345_Customer")
        assert valid.is_valid() == True
        
        invalid = JobFolderParser.parse("NoJobNumber")
        assert invalid.is_valid() == False

    def test_get_method(self):
        """Test dictionary-like get method"""
        result = JobFolderParser.parse("12345_JohnDoe")
        
        assert result.get("job_number") == "12345"
        assert result.get("nonexistent", "default") == "default"

    def test_parse_date_based_full_format(self):
        """Date-based job number (YYYYMMDD-N) parses as the full job number"""
        folder = "20260620-1_JohnDoe_AcmeCorp_MUG-11OZ x 100_(PO-98765)"
        result = JobFolderParser.parse(folder)

        assert result.job_number == "20260620-1"
        assert result.job_date == "2026-06-20"
        assert result.date_sequence == "1"
        assert result.date_source == "name"
        assert result.customer == "JohnDoe"
        assert result.company == "AcmeCorp"
        assert result.sku == "MUG-11OZ"
        assert result.quantity == "100"
        assert result.po_number == "PO-98765"

    def test_parse_date_based_no_sequence(self):
        """Compact date without a -N sequence still parses"""
        result = JobFolderParser.parse("20260620_JohnDoe")
        assert result.job_number == "20260620"
        assert result.job_date == "2026-06-20"
        assert result.date_sequence == ""
        assert result.date_source == "name"

    def test_parse_numeric_job_has_no_date(self):
        """Old-style numeric jobs carry no date and no name-source flag"""
        result = JobFolderParser.parse("12345_JohnDoe")
        assert result.job_number == "12345"
        assert result.job_date == ""
        assert result.date_source == ""

    def test_eight_digit_non_date_is_not_treated_as_date(self):
        """An 8-digit count that isn't a valid date is not parsed as a date"""
        result = JobFolderParser.parse("99999999_JohnDoe")
        assert result.job_date == ""
        assert result.date_source == ""

    def test_parse_format_a_production(self):
        """Real production format: J<date>-<seq> (Customer @ Company) <SKU>"""
        folder = "J20260603-1 (Janelle Nelson @ Her Request) KC Royals branding"
        result = JobFolderParser.parse(folder)

        assert result.job_number == "J20260603-1"
        assert result.job_date == "2026-06-03"
        assert result.date_sequence == "1"
        assert result.date_source == "name"
        assert result.customer == "Janelle Nelson"
        assert result.company == "Her Request"
        assert result.sku == "KC Royals branding"
        assert result.quantity == ""

    def test_parse_format_a_qty_and_po(self):
        """Trailing 'x<n>' is the quantity; trailing [..]/(..) is the PO marker"""
        folder = "J20211016-1 (MasSaSeen @ Avalon Gardens) Pro_SimpleRTK_GNSS_Case x3 [PO# NotYet]"
        result = JobFolderParser.parse(folder)

        assert result.job_number == "J20211016-1"
        assert result.job_date == "2021-10-16"
        assert result.customer == "MasSaSeen"
        assert result.company == "Avalon Gardens"
        assert result.sku == "Pro_SimpleRTK_GNSS_Case"
        assert result.quantity == "3"
        assert result.po_number == "NotYet"

    def test_parse_format_a_sku_with_x_not_quantity(self):
        """A SKU ending in letters+digits (no space before x) isn't a quantity"""
        result = JobFolderParser.parse("J20211016-1 (Cust @ Co) WidgetBox2")
        assert result.sku == "WidgetBox2"
        assert result.quantity == ""

    def test_parse_format_a_no_trailing_sku(self):
        """Format A with no trailing text leaves SKU empty"""
        result = JobFolderParser.parse("J20260603-2 (Bob Smith @ Acme)")
        assert result.job_number == "J20260603-2"
        assert result.job_date == "2026-06-03"
        assert result.customer == "Bob Smith"
        assert result.company == "Acme"
        assert result.sku == ""

    def test_parse_format_a_no_at_separator(self):
        """Without '@', the parenthesized text is treated as the customer"""
        result = JobFolderParser.parse("J20260603-1 (Janelle Nelson) Some SKU")
        assert result.customer == "Janelle Nelson"
        assert result.company == ""
        assert result.sku == "Some SKU"

    def test_validate_folder_name(self):
        """Test folder name validation"""
        valid, msg = JobFolderParser.validate_folder_name("12345_Customer")
        assert valid == True

        # Date-based job numbers are also valid
        valid, msg = JobFolderParser.validate_folder_name("20260620-1_Customer")
        assert valid == True

        valid, msg = JobFolderParser.validate_folder_name("")
        assert valid == False
        assert "empty" in msg.lower()

    def test_suggest_folder_name(self):
        """Test folder name suggestion"""
        suggested = JobFolderParser.suggest_folder_name(
            job_number="12345",
            customer="John Doe",
            company="Acme Corp",
            sku="MUG-11OZ",
            quantity="100",
            po_number="PO-98765"
        )
        
        assert "12345" in suggested
        assert "JohnDoe" in suggested
        assert "MUG-11OZ" in suggested
        assert "100" in suggested
        assert "PO-98765" in suggested


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
