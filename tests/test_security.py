
import pytest
from pathlib import Path
import os
from tools import read_file, write_file, list_files, delete_file, run_command, _validate_path
from config import get_config

class TestSecurity:
    
    def test_validate_path_inside(self):
        """Test that validating a path inside the project root succeeds."""
        config = get_config()
        # Should not raise exception
        # We use must_exist=False because the file might not exist
        path = _validate_path("some_file.txt", must_exist=False)
        assert str(path).startswith(str(config.project_root.resolve()))

    def test_validate_path_outside_relative(self):
        """Test that validating a relative path outside the project root fails."""
        with pytest.raises(PermissionError):
            _validate_path("../outside_file.txt", must_exist=False)
            
    def test_validate_path_outside_absolute(self):
        """Test that validating an absolute path outside the project root fails."""
        # Using a path that is definitely outside, e.g., root of drive or temp
        outside_path = Path("C:/") if os.name == 'nt' else Path("/")
        with pytest.raises(PermissionError):
            _validate_path(outside_path / "test.txt", must_exist=False)

    def test_read_file_security(self):
        """Test that read_file blocks access to files outside project root."""
        # We expect the function to catch the PermissionError and return an error string
        result = read_file("../outside.txt")
        assert "Error:" in result
        assert "outside project root" in result or "Permission denied" in result

    def test_write_file_security(self):
        """Test that write_file blocks writing to files outside project root."""
        result = write_file("../outside.txt", "content")
        assert "Error:" in result
        assert "outside project root" in result or "Permission denied" in result

    def test_list_files_security(self):
        """Test that list_files blocks listing directories outside project root."""
        result = list_files("../")
        assert "Error:" in result
        assert "outside project root" in result or "Permission denied" in result

    def test_run_command_cwd_security(self):
        """Test that run_command blocks execution in cwd outside project root."""
        result = run_command("echo hello", cwd="../")
        assert "Error:" in result
        assert "Working directory must be within project root" in result
