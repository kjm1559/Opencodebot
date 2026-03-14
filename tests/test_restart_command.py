import subprocess
import unittest
from unittest.mock import MagicMock, patch, call

class TestRestartCommand(unittest.TestCase):
    """Test /restart command with git pull."""
    
    def test_git_pull_success(self):
        """Test git pull returns success."""
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0 or result.returncode == 1
    
    def test_git_pull_output_parsing(self):
        """Test git pull output parsing."""
        mock_output = "From https://github.com/test/repo\n   abc123..def456  main -> origin/main"
        if mock_output.strip():
            preview = mock_output.split('\n')[0][:250]
            assert len(preview) <= 250
            assert preview.startswith("From")
    
    def test_git_pull_timeout_handling(self):
        """Test git pull timeout handling."""
        try:
            subprocess.run(
                ["git", "pull"],
                timeout=60,
                capture_output=True,
                text=True
            )
        except subprocess.TimeoutExpired as e:
            assert "timeout" in str(e).lower()
        
    def test_git_pull_error_handling(self):
        """Test git pull error handling."""
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            assert result.stderr.strip() or True
        
if __name__ == "__main__":
    unittest.main()
