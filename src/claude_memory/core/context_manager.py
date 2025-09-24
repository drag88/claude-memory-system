"""
Project Context Manager for automated project understanding and onboarding.

Implements context engineering best practices for codebase understanding,
providing lightweight project discovery and intelligent context assembly.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta


class ProjectContext:
    """
    Manages project-specific context information for intelligent session initialization.

    Follows context engineering principles:
    - Comprehensive context assembly
    - Lightweight discovery with caching
    - Progressive enhancement
    - Project-aware templates
    """

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize context manager.

        Args:
            project_path: Path to project root (defaults to current directory)
        """
        self.project_path = project_path or Path.cwd()
        self.context_dir = self.project_path / ".claude" / "memories" / ".context"
        self.context_file = self.context_dir / "project-context.json"
        self.cache_duration = timedelta(days=7)  # Refresh context weekly

    def get_session_context(self) -> str:
        """
        Get formatted context for Claude session initialization.

        Returns:
            Formatted context string ready for session
        """
        context_data = self._load_or_gather_context()
        return self._format_context(context_data)

    def refresh_context(self) -> Dict[str, Any]:
        """
        Force refresh of project context.

        Returns:
            Updated context data
        """
        return self._gather_context(force_refresh=True)

    def clear_context(self) -> bool:
        """
        Clear cached context.

        Returns:
            True if cleared successfully
        """
        try:
            if self.context_file.exists():
                self.context_file.unlink()
            return True
        except Exception:
            return False

    def _load_or_gather_context(self) -> Dict[str, Any]:
        """Load cached context or gather fresh if needed."""
        if self._is_cache_valid():
            return self._load_cached_context()
        return self._gather_context()

    def _is_cache_valid(self) -> bool:
        """Check if cached context is still valid."""
        if not self.context_file.exists():
            return False

        try:
            cache_time = datetime.fromtimestamp(self.context_file.stat().st_mtime)
            return datetime.now() - cache_time < self.cache_duration
        except Exception:
            return False

    def _load_cached_context(self) -> Dict[str, Any]:
        """Load context from cache."""
        try:
            with open(self.context_file, 'r') as f:
                return json.load(f)
        except Exception:
            return self._gather_context()

    def _gather_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Gather comprehensive project context.

        Args:
            force_refresh: Force regathering even if cache is valid

        Returns:
            Complete context data dictionary
        """
        context_data = {
            "project_name": self._detect_project_name(),
            "project_type": self._detect_project_type(),
            "primary_language": self._detect_primary_language(),
            "project_path": str(self.project_path),
            "tech_stack": self._detect_tech_stack(),
            "available_commands": self._extract_available_commands(),
            "directory_structure": self._get_directory_structure(),
            "recent_commits": self._get_recent_commits(),
            "key_files": self._identify_key_files(),
            "project_metrics": self._calculate_project_metrics(),
            "gathered_at": datetime.now().isoformat()
        }

        self._cache_context(context_data)
        return context_data

    def _detect_project_name(self) -> str:
        """Detect project name from various sources."""
        # Try package.json
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    return data.get("name", self.project_path.name)
            except Exception:
                pass

        # Try pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                for line in content.split('\n'):
                    if line.strip().startswith('name ='):
                        return line.split('=')[1].strip().strip('"\'')
            except Exception:
                pass

        # Try setup.py
        setup_py = self.project_path / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                for line in content.split('\n'):
                    if 'name=' in line:
                        # Simple extraction, could be improved
                        parts = line.split('name=')[1].split(',')[0]
                        return parts.strip().strip('"\'')
            except Exception:
                pass

        # Fallback to directory name
        return self.project_path.name

    def _detect_project_type(self) -> str:
        """Detect project type based on files and structure."""
        # Check for specific files that indicate project type
        if (self.project_path / "package.json").exists():
            return "Node.js"
        if (self.project_path / "pyproject.toml").exists() or (self.project_path / "requirements.txt").exists():
            return "Python"
        if (self.project_path / "go.mod").exists():
            return "Go"
        if (self.project_path / "Cargo.toml").exists():
            return "Rust"
        if (self.project_path / "pom.xml").exists():
            return "Java (Maven)"
        if (self.project_path / "build.gradle").exists():
            return "Java (Gradle)"
        if (self.project_path / "composer.json").exists():
            return "PHP"
        if (self.project_path / "Gemfile").exists():
            return "Ruby"

        return "Unknown"

    def _detect_primary_language(self) -> str:
        """Detect primary programming language."""
        language_files = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".php": "PHP",
            ".rb": "Ruby",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#"
        }

        counts = {}
        try:
            for root, _, files in os.walk(self.project_path):
                # Skip hidden directories and common ignore patterns
                if any(part.startswith('.') for part in Path(root).parts[len(self.project_path.parts):]):
                    continue
                if any(ignore in root for ignore in ['node_modules', '__pycache__', 'venv', '.git']):
                    continue

                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in language_files:
                        lang = language_files[ext]
                        counts[lang] = counts.get(lang, 0) + 1
        except Exception:
            pass

        if counts:
            return max(counts, key=counts.get)
        return "Unknown"

    def _detect_tech_stack(self) -> List[str]:
        """Detect technology stack from project files."""
        tech_stack = []

        # Web frameworks
        if (self.project_path / "package.json").exists():
            try:
                with open(self.project_path / "package.json") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                    if "react" in deps:
                        tech_stack.append("React")
                    if "vue" in deps:
                        tech_stack.append("Vue.js")
                    if "angular" in deps:
                        tech_stack.append("Angular")
                    if "next" in deps:
                        tech_stack.append("Next.js")
                    if "express" in deps:
                        tech_stack.append("Express.js")
            except Exception:
                pass

        # Python frameworks
        req_files = [
            self.project_path / "requirements.txt",
            self.project_path / "pyproject.toml"
        ]

        for req_file in req_files:
            if req_file.exists():
                try:
                    content = req_file.read_text().lower()
                    if "fastapi" in content:
                        tech_stack.append("FastAPI")
                    if "django" in content:
                        tech_stack.append("Django")
                    if "flask" in content:
                        tech_stack.append("Flask")
                    if "streamlit" in content:
                        tech_stack.append("Streamlit")
                    if "pytorch" in content:
                        tech_stack.append("PyTorch")
                    if "tensorflow" in content:
                        tech_stack.append("TensorFlow")
                except Exception:
                    pass

        # Infrastructure
        if (self.project_path / "Dockerfile").exists():
            tech_stack.append("Docker")
        if (self.project_path / "docker-compose.yml").exists():
            tech_stack.append("Docker Compose")
        if (self.project_path / "deployment").exists():
            tech_stack.append("Kubernetes")

        return tech_stack

    def _extract_available_commands(self) -> Dict[str, str]:
        """Extract available commands from package files."""
        commands = {}

        # package.json scripts
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})
                    for name, cmd in scripts.items():
                        if name in ["test", "build", "start", "dev", "lint", "format"]:
                            commands[name] = f"npm run {name}"
            except Exception:
                pass

        # pyproject.toml scripts
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "[tool.poe.tasks]" in content:
                    # Poethepoet tasks detected - parse more carefully
                    lines = content.split('\n')
                    in_poe_section = False
                    for line in lines:
                        line = line.strip()
                        if line == "[tool.poe.tasks]":
                            in_poe_section = True
                            continue
                        elif line.startswith('[') and in_poe_section:
                            # Entered a different section
                            break
                        elif in_poe_section and '=' in line:
                            # Parse task definition
                            task_name = line.split('=')[0].strip().strip('"\'')
                            if task_name in ["test", "lint", "format", "type-check", "build"]:
                                commands[task_name] = f"uv run poe {task_name}"
            except Exception:
                pass

        # Common Python commands
        if (self.project_path / "pytest.ini").exists() or "pytest" in str(self.project_path):
            commands.setdefault("test", "uv run pytest")

        # Makefile
        makefile = self.project_path / "Makefile"
        if makefile.exists():
            try:
                content = makefile.read_text()
                for line in content.split('\n'):
                    if ':' in line and not line.startswith('\t'):
                        target = line.split(':')[0].strip()
                        if target in ["test", "build", "clean", "install"]:
                            commands[target] = f"make {target}"
            except Exception:
                pass

        return commands

    def _get_directory_structure(self) -> str:
        """Get simplified directory structure."""
        structure_lines = []

        def add_directory(path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0):
            if current_depth >= max_depth:
                return

            items = []
            try:
                for item in sorted(path.iterdir()):
                    # Skip hidden files and common ignore patterns
                    if item.name.startswith('.'):
                        continue
                    if item.name in ['node_modules', '__pycache__', 'venv', 'env']:
                        continue
                    items.append(item)
            except (PermissionError, FileNotFoundError, OSError):
                return

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                structure_lines.append(f"{prefix}{current_prefix}{item.name}/")

                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    add_directory(item, next_prefix, max_depth, current_depth + 1)

        try:
            structure_lines.append(f"{self.project_path.name}/")
            add_directory(self.project_path)
        except (FileNotFoundError, OSError):
            structure_lines.append("Project structure unavailable")

        return '\n'.join(structure_lines[:20])  # Limit to 20 lines

    def _get_recent_commits(self) -> List[Dict[str, str]]:
        """Get recent git commits."""
        commits = []
        try:
            result = subprocess.run([
                "git", "log", "--oneline", "-5", "--pretty=format:%h|%s|%cr"
            ], cwd=self.project_path, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|', 2)
                        if len(parts) == 3:
                            commits.append({
                                "hash": parts[0],
                                "message": parts[1],
                                "time": parts[2]
                            })
        except Exception:
            pass

        return commits

    def _identify_key_files(self) -> List[str]:
        """Identify key project files."""
        key_files = []

        important_files = [
            "README.md", "CONTRIBUTING.md", "LICENSE",
            "package.json", "pyproject.toml", "requirements.txt",
            "Dockerfile", "docker-compose.yml",
            "Makefile", ".gitignore"
        ]

        for file_name in important_files:
            if (self.project_path / file_name).exists():
                key_files.append(file_name)

        return key_files

    def _calculate_project_metrics(self) -> Dict[str, Any]:
        """Calculate basic project metrics."""
        metrics = {
            "total_files": 0,
            "code_files": 0,
            "estimated_size": "Unknown"
        }

        try:
            file_count = 0
            code_count = 0
            code_extensions = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.php', '.rb'}

            for root, _, files in os.walk(self.project_path):
                # Skip hidden and common ignore directories
                if any(part.startswith('.') for part in Path(root).parts[len(self.project_path.parts):]):
                    continue
                if any(ignore in root for ignore in ['node_modules', '__pycache__', 'venv']):
                    continue

                for file in files:
                    file_count += 1
                    if Path(file).suffix.lower() in code_extensions:
                        code_count += 1

            metrics["total_files"] = file_count
            metrics["code_files"] = code_count

            # Estimate project size
            if code_count < 10:
                metrics["estimated_size"] = "Small"
            elif code_count < 100:
                metrics["estimated_size"] = "Medium"
            else:
                metrics["estimated_size"] = "Large"

        except Exception:
            pass

        return metrics

    def _cache_context(self, context_data: Dict[str, Any]) -> None:
        """Cache context data to disk."""
        try:
            self.context_dir.mkdir(parents=True, exist_ok=True)
            with open(self.context_file, 'w') as f:
                json.dump(context_data, f, indent=2, default=str)
        except Exception:
            pass  # Fail silently if caching fails

    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """Format context data for Claude session."""
        project_name = context_data.get("project_name", "Unknown")
        project_type = context_data.get("project_type", "Unknown")
        primary_language = context_data.get("primary_language", "Unknown")
        tech_stack = context_data.get("tech_stack", [])
        commands = context_data.get("available_commands", {})
        structure = context_data.get("directory_structure", "")
        commits = context_data.get("recent_commits", [])
        metrics = context_data.get("project_metrics", {})

        # Build formatted context
        context_lines = [
            f"## 📋 Project Context: {project_name}",
            f"**Type:** {project_type} | **Language:** {primary_language}",
            f"**Size:** {metrics.get('estimated_size', 'Unknown')} ({metrics.get('code_files', 0)} code files)",
            ""
        ]

        # Commands section
        if commands:
            context_lines.append("### 🔧 Available Commands")
            for cmd_type, cmd in sorted(commands.items()):
                context_lines.append(f"• **{cmd_type.title()}:** `{cmd}`")
            context_lines.append("")

        # Tech stack
        if tech_stack:
            context_lines.append(f"### 💻 Tech Stack")
            context_lines.append(f"{', '.join(tech_stack)}")
            context_lines.append("")

        # Directory structure
        if structure:
            context_lines.append("### 📁 Project Structure")
            context_lines.append("```")
            context_lines.append(structure)
            context_lines.append("```")
            context_lines.append("")

        # Recent commits
        if commits:
            context_lines.append("### 🔄 Recent Changes")
            for commit in commits[:3]:  # Show only last 3
                context_lines.append(f"• `{commit['hash']}` {commit['message']} ({commit['time']})")
            context_lines.append("")

        context_lines.append("*Context auto-generated and cached for 7 days*")

        return '\n'.join(context_lines)