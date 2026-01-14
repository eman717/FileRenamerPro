"""Tests for utility functions"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.utils import (
    sanitize_filename, 
    validate_filename, 
    get_unique_path,
    parse_dropped_files,
    get_file_size_str,
)


class TestSanitizeFilename:
    """Tests for sanitize_filename function"""

    def test_removes_invalid_characters(self):
        """Test that invalid characters are removed"""
        result = sanitize_filename('file<>:"/\\|?*.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved"""
        result = sanitize_filename("valid_file-name.txt")
        assert result == "valid_file-name.txt"

    def test_handles_empty_string(self):
        """Test empty string handling"""
        result = sanitize_filename("")
        assert result == ""

    def test_handles_reserved_names(self):
        """Test Windows reserved names"""
        result = sanitize_filename("CON.txt")
        assert result != "CON.txt"
        assert "CON" in result

    def test_trims_spaces_and_dots(self):
        """Test trimming of leading/trailing spaces and dots"""
        result = sanitize_filename("  file.txt  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_limits_length(self):
        """Test filename length limiting"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 200


class TestValidateFilename:
    """Tests for validate_filename function"""

    def test_valid_filename(self):
        """Test valid filename"""
        valid, msg = validate_filename("valid_file.txt")
        assert valid == True
        assert msg == ""

    def test_empty_filename(self):
        """Test empty filename"""
        valid, msg = validate_filename("")
        assert valid == False
        assert "empty" in msg.lower()

    def test_invalid_characters(self):
        """Test invalid characters"""
        valid, msg = validate_filename("file<name>.txt")
        assert valid == False
        assert "invalid" in msg.lower()

    def test_reserved_names(self):
        """Test reserved names"""
        valid, msg = validate_filename("CON")
        assert valid == False
        assert "reserved" in msg.lower()


class TestGetUniquePath:
    """Tests for get_unique_path function"""

    def test_returns_same_if_not_exists(self):
        """Test returns same path if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "newfile.txt"
            result = get_unique_path(path)
            assert result == path

    def test_increments_if_exists(self):
        """Test increments if file exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.txt"
            path.touch()  # Create the file
            
            result = get_unique_path(path)
            assert result != path
            assert "file_1.txt" in str(result)


class TestParseDroppedFiles:
    """Tests for parse_dropped_files function"""

    def test_simple_paths(self):
        """Test simple space-separated paths"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            file1.touch()
            file2.touch()
            
            data = f"{file1} {file2}"
            result = parse_dropped_files(data)
            
            assert len(result) == 2
            assert str(file1) in result
            assert str(file2) in result

    def test_braced_paths(self):
        """Test paths with braces (Windows with spaces)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file1.touch()
            
            data = f"{{{file1}}}"
            result = parse_dropped_files(data)
            
            assert len(result) == 1

    def test_filters_nonexistent(self):
        """Test that non-existent files are filtered out"""
        data = "/nonexistent/path/file.txt /another/fake/path.txt"
        result = parse_dropped_files(data)
        assert len(result) == 0


class TestGetFileSizeStr:
    """Tests for get_file_size_str function"""

    def test_bytes(self):
        """Test bytes display"""
        result = get_file_size_str(500)
        assert "500" in result
        assert "B" in result

    def test_kilobytes(self):
        """Test kilobytes display"""
        result = get_file_size_str(2048)
        assert "KB" in result

    def test_megabytes(self):
        """Test megabytes display"""
        result = get_file_size_str(2 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        """Test gigabytes display"""
        result = get_file_size_str(2 * 1024 * 1024 * 1024)
        assert "GB" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
