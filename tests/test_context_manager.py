"""
Tests for ProjectContext and context management functionality.

Tests cover project discovery, context caching, template formatting,
and integration with the memory system.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from claude_memory.core.context_manager import ProjectContext


class TestProjectContext(unittest.TestCase):
    """Test ProjectContext class functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        self.context = ProjectContext(self.project_path)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test ProjectContext initialization."""
        # Test default path
        default_context = ProjectContext()
        self.assertEqual(default_context.project_path, Path.cwd())

        # Test custom path
        self.assertEqual(self.context.project_path, self.project_path)
        self.assertTrue(str(self.context.context_dir).endswith(".claude/memories/.context"))

    def test_detect_project_name(self):
        """Test project name detection from various sources."""
        # Test from directory name (fallback)
        name = self.context._detect_project_name()
        self.assertEqual(name, self.project_path.name)

        # Test from package.json
        package_json = self.project_path / "package.json"
        package_json.write_text(json.dumps({"name": "test-project"}))
        name = self.context._detect_project_name()
        self.assertEqual(name, "test-project")

        # Test from pyproject.toml
        package_json.unlink()
        pyproject = self.project_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry]\nname = "poetry-project"\n')
        name = self.context._detect_project_name()
        self.assertEqual(name, "poetry-project")

    def test_detect_project_type(self):
        """Test project type detection."""
        # Test unknown type (default)
        project_type = self.context._detect_project_type()
        self.assertEqual(project_type, "Unknown")

        # Test Node.js project
        package_json = self.project_path / "package.json"
        package_json.write_text("{}")
        project_type = self.context._detect_project_type()
        self.assertEqual(project_type, "Node.js")

        # Test Python project
        package_json.unlink()
        pyproject = self.project_path / "pyproject.toml"
        pyproject.write_text("")
        project_type = self.context._detect_project_type()
        self.assertEqual(project_type, "Python")

        # Test Go project
        pyproject.unlink()
        go_mod = self.project_path / "go.mod"
        go_mod.write_text("")
        project_type = self.context._detect_project_type()
        self.assertEqual(project_type, "Go")

    def test_detect_primary_language(self):
        """Test primary language detection."""
        # Test with Python files
        (self.project_path / "main.py").write_text("print('hello')")
        (self.project_path / "utils.py").write_text("def hello(): pass")

        language = self.context._detect_primary_language()
        self.assertEqual(language, "Python")

        # Test with mixed files (Python should still win)
        (self.project_path / "app.js").write_text("console.log('hello')")
        language = self.context._detect_primary_language()
        self.assertEqual(language, "Python")

    def test_detect_tech_stack(self):
        """Test technology stack detection."""
        # Test with package.json dependencies
        package_json = self.project_path / "package.json"
        package_json.write_text(json.dumps({
            "dependencies": {"react": "^18.0.0", "express": "^4.18.0"},
            "devDependencies": {"typescript": "^4.8.0"}
        }))

        tech_stack = self.context._detect_tech_stack()
        self.assertIn("React", tech_stack)
        self.assertIn("Express.js", tech_stack)

        # Test with Python requirements
        package_json.unlink()
        requirements = self.project_path / "requirements.txt"
        requirements.write_text("fastapi==0.95.0\npytest==7.0.0\n")

        tech_stack = self.context._detect_tech_stack()
        self.assertIn("FastAPI", tech_stack)

        # Test with Docker
        dockerfile = self.project_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11\n")

        tech_stack = self.context._detect_tech_stack()
        self.assertIn("Docker", tech_stack)

    def test_extract_available_commands(self):
        """Test command extraction from project files."""
        # Test npm scripts
        package_json = self.project_path / "package.json"
        package_json.write_text(json.dumps({
            "scripts": {
                "test": "jest",
                "build": "webpack",
                "start": "node server.js",
                "lint": "eslint ."
            }
        }))

        commands = self.context._extract_available_commands()
        self.assertEqual(commands["test"], "npm run test")
        self.assertEqual(commands["build"], "npm run build")
        self.assertEqual(commands["lint"], "npm run lint")

        # Test with Makefile
        package_json.unlink()
        makefile = self.project_path / "Makefile"
        makefile.write_text("test:\n\tpytest\n\nbuild:\n\tpython setup.py build\n")

        commands = self.context._extract_available_commands()
        self.assertEqual(commands["test"], "make test")
        self.assertEqual(commands["build"], "make build")

    def test_get_directory_structure(self):
        """Test directory structure generation."""
        # Create test directory structure
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text("")
        (self.project_path / "tests").mkdir()
        (self.project_path / "tests" / "test_main.py").write_text("")
        (self.project_path / "README.md").write_text("")

        structure = self.context._get_directory_structure()

        # Check that main directories are included
        self.assertIn("src/", structure)
        self.assertIn("tests/", structure)
        self.assertIn("README.md", structure)

    @patch('subprocess.run')
    def test_get_recent_commits(self, mock_run):
        """Test git commit retrieval."""
        # Mock successful git log output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123|feat: add new feature|2 hours ago\ndef456|fix: bug fix|1 day ago"
        mock_run.return_value = mock_result

        commits = self.context._get_recent_commits()

        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]["hash"], "abc123")
        self.assertEqual(commits[0]["message"], "feat: add new feature")
        self.assertEqual(commits[0]["time"], "2 hours ago")

        # Test with git command failure
        mock_result.returncode = 1
        commits = self.context._get_recent_commits()
        self.assertEqual(commits, [])

    def test_identify_key_files(self):
        """Test key file identification."""
        # Create some key files
        (self.project_path / "README.md").write_text("")
        (self.project_path / "package.json").write_text("{}")
        (self.project_path / "Dockerfile").write_text("")
        (self.project_path / ".gitignore").write_text("")

        key_files = self.context._identify_key_files()

        self.assertIn("README.md", key_files)
        self.assertIn("package.json", key_files)
        self.assertIn("Dockerfile", key_files)
        self.assertIn(".gitignore", key_files)

    def test_calculate_project_metrics(self):
        """Test project metrics calculation."""
        # Create test files
        (self.project_path / "app.py").write_text("print('hello')")
        (self.project_path / "utils.py").write_text("def test(): pass")
        (self.project_path / "README.md").write_text("# Project")
        (self.project_path / "data.json").write_text("{}")

        metrics = self.context._calculate_project_metrics()

        self.assertEqual(metrics["code_files"], 2)  # .py files
        self.assertEqual(metrics["total_files"], 4)  # all files
        self.assertEqual(metrics["estimated_size"], "Small")  # < 10 code files

    def test_cache_context(self):
        """Test context caching functionality."""
        test_data = {
            "project_name": "test-project",
            "project_type": "Python",
            "gathered_at": "2024-01-01T00:00:00"
        }

        # Test caching
        self.context._cache_context(test_data)
        self.assertTrue(self.context.context_file.exists())

        # Test loading cached data
        cached_data = self.context._load_cached_context()
        self.assertEqual(cached_data["project_name"], "test-project")
        self.assertEqual(cached_data["project_type"], "Python")

    def test_is_cache_valid(self):
        """Test cache validity checking."""
        # No cache file
        self.assertFalse(self.context._is_cache_valid())

        # Create cache file
        test_data = {"test": "data"}
        self.context._cache_context(test_data)

        # Should be valid (just created)
        self.assertTrue(self.context._is_cache_valid())

    def test_format_context(self):
        """Test context formatting."""
        context_data = {
            "project_name": "test-project",
            "project_type": "Python",
            "primary_language": "Python",
            "tech_stack": ["FastAPI", "Docker"],
            "available_commands": {"test": "pytest", "lint": "ruff"},
            "directory_structure": "test-project/\n├── src/\n└── tests/",
            "recent_commits": [
                {"hash": "abc123", "message": "feat: add feature", "time": "2 hours ago"}
            ],
            "project_metrics": {"estimated_size": "Small", "code_files": 5}
        }

        formatted = self.context._format_context(context_data)

        # Check essential elements are present
        self.assertIn("test-project", formatted)
        self.assertIn("Python", formatted)
        self.assertIn("FastAPI", formatted)
        self.assertIn("pytest", formatted)
        self.assertIn("abc123", formatted)
        self.assertIn("Small", formatted)

    def test_get_session_context(self):
        """Test session context generation."""
        # Create minimal project structure
        (self.project_path / "README.md").write_text("# Test Project")
        (self.project_path / "main.py").write_text("print('hello')")

        context = self.context.get_session_context()

        # Should be a non-empty string
        self.assertIsInstance(context, str)
        self.assertTrue(len(context) > 0)

        # Should contain project information
        self.assertIn("Project Context", context)

    def test_refresh_context(self):
        """Test context refresh functionality."""
        # Create project files
        (self.project_path / "app.py").write_text("print('hello')")

        # Initial context
        context_data = self.context.refresh_context()

        self.assertIn("project_name", context_data)
        self.assertIn("project_type", context_data)
        self.assertIn("gathered_at", context_data)

    def test_clear_context(self):
        """Test context clearing."""
        # Create cached context
        test_data = {"test": "data"}
        self.context._cache_context(test_data)
        self.assertTrue(self.context.context_file.exists())

        # Clear context
        result = self.context.clear_context()
        self.assertTrue(result)
        self.assertFalse(self.context.context_file.exists())

        # Clear non-existent context
        result = self.context.clear_context()
        self.assertTrue(result)  # Should still return True


class TestProjectContextIntegration(unittest.TestCase):
    """Test ProjectContext integration with memory system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)

        # Create a realistic project structure
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text("def main(): pass")
        (self.project_path / "tests").mkdir()
        (self.project_path / "tests" / "test_main.py").write_text("def test_main(): pass")
        (self.project_path / "README.md").write_text("# Test Project")
        (self.project_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "A test project"

[tool.poe.tasks]
test = "pytest"
lint = "ruff check ."
format = "ruff format ."
""")

        self.context = ProjectContext(self.project_path)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_full_context_generation(self):
        """Test complete context generation process."""
        # Generate full context
        context_text = self.context.get_session_context()

        # Verify all major sections are present
        self.assertIn("Project Context: test-project", context_text)
        self.assertIn("Python", context_text)  # Project type/language
        self.assertIn("Available Commands", context_text)
        self.assertIn("Project Structure", context_text)
        self.assertIn("uv run poe", context_text)  # Should detect poe commands

    def test_context_caching_behavior(self):
        """Test context caching and refresh behavior."""
        # First call should generate and cache
        context1 = self.context.get_session_context()
        self.assertTrue(self.context.context_file.exists())

        # Second call should use cache
        context2 = self.context.get_session_context()
        self.assertEqual(context1, context2)

        # Refresh should regenerate
        self.context.refresh_context()
        context3 = self.context.get_session_context()

        # Content might be same, but timestamp should be different
        self.assertIsInstance(context3, str)
        self.assertTrue(len(context3) > 0)

    @patch('subprocess.run')
    def test_git_integration(self, mock_run):
        """Test git integration in context generation."""
        # Mock git log success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123|feat: add new feature|2 hours ago\ndef456|fix: bug fix|1 day ago"
        mock_run.return_value = mock_result

        context_text = self.context.get_session_context()

        # Should include recent commits
        self.assertIn("Recent Changes", context_text)
        self.assertIn("abc123", context_text)
        self.assertIn("feat: add new feature", context_text)

    def test_error_handling(self):
        """Test error handling in context generation."""
        # Test with invalid project path
        invalid_context = ProjectContext(Path("/nonexistent/path"))

        # Should not crash, should handle gracefully
        try:
            context_text = invalid_context.get_session_context()
            # Should still return some context, even if basic
            self.assertIsInstance(context_text, str)
        except Exception as e:
            self.fail(f"Context generation should handle errors gracefully: {e}")


if __name__ == "__main__":
    unittest.main()