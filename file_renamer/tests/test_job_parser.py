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

    def test_validate_folder_name(self):
        """Test folder name validation"""
        valid, msg = JobFolderParser.validate_folder_name("12345_Customer")
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
